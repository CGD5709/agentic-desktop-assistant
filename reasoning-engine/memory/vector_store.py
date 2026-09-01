import os
import asyncio
from typing import List, Optional, Dict, Any, Sequence, Mapping
from datetime import datetime, timezone
import chromadb
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection
from chromadb.api.types import Where
from langchain_ollama import OllamaEmbeddings
from memory.models import MemoryItem, MemoryCategory

# Default vector store configuration
DEFAULT_PERSIST_DIR = "./data/chroma_db"
DEFAULT_COLLECTION_NAME = "jarvis_long_term_memory"
DEFAULT_EMBEDDING_MODEL = "nomic-embed-text"
DEFAULT_OLLAMA_URL = "http://localhost:11434"

# Default retrieval and scoring parameters
DEFAULT_SEARCH_LIMIT = 4
DEFAULT_SCORE_THRESHOLD = 0.65
DEFAULT_IMPORTANCE_SCORE = 3
SIMILARITY_PRECISION = 3


def _sanitize_metadata(raw_meta: Mapping[str, Any]) -> Dict[str, Any]:
    """
    Sanitizes metadata dictionary for ChromaDB compatibility.
    ChromaDB only supports primitive types (str, int, float, bool) as metadata values.
    Converts None or complex types into compatible representations.
    """
    clean: Dict[str, Any] = {}
    for k, v in raw_meta.items():
        if v is None:
            clean[k] = ""
        elif isinstance(v, (str, int, float, bool)):
            clean[k] = v
        elif isinstance(v, MemoryCategory):
            clean[k] = v.value
        else:
            clean[k] = str(v)
    return clean


class VectorMemoryStore:
    """
    Level 2 Memory: Semantic Long-Term Memory (RAG).
    Persists cross-session memories in a local ChromaDB vector database
    using Ollama embeddings (e.g., nomic-embed-text).
    """

    def __init__(
        self,
        persist_directory: str = DEFAULT_PERSIST_DIR,
        collection_name: str = DEFAULT_COLLECTION_NAME,
        embedding_model: str = DEFAULT_EMBEDDING_MODEL,
        ollama_base_url: str = DEFAULT_OLLAMA_URL
    ) -> None:
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        self.ollama_base_url = ollama_base_url
        self._client: Optional[ClientAPI] = None
        self._collection: Optional[Collection] = None
        self._embeddings: Optional[OllamaEmbeddings] = None

    def _initialize(self) -> None:
        """
        Synchronously initializes ChromaDB client, collection, and embedding model.
        Implements lazy loading to defer connection overhead until first access.
        """
        if self._client is None:
            os.makedirs(os.path.abspath(self.persist_directory), exist_ok=True)
            self._client = chromadb.PersistentClient(path=self.persist_directory)
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            self._embeddings = OllamaEmbeddings(
                model=self.embedding_model,
                base_url=self.ollama_base_url
            )

    async def initialize(self) -> None:
        """Asynchronously initializes the vector store off the main event loop."""
        await asyncio.to_thread(self._initialize)

    async def _get_embedding(self, text: str) -> List[float]:
        """
        Generates vector embeddings for a given text using the configured Ollama model.
        
        Returns:
            List[float]: The embedding vector, or an empty list if generation fails.
        """
        self._initialize()
        assert self._embeddings is not None
        try:
            return await asyncio.to_thread(self._embeddings.embed_query, text)
        except Exception as e:
            # TODO: Replace with proper logger
            print(f"⚠️ [VectorStore] Error generating embedding with Ollama ({self.embedding_model}): {e}")
            return []

    async def add_memory(self, item: MemoryItem) -> bool:
        """
        Persists a new memory item with its computed embedding and sanitized metadata.
        
        Returns:
            bool: True if the item was successfully stored, False otherwise.
        """
        try:
            embedding = await self._get_embedding(item.text)
            if not embedding:
                return False

            cat_str = item.category.value if isinstance(item.category, MemoryCategory) else str(item.category or "FACT")
            raw_metadata: Dict[str, Any] = {
                "category": cat_str,
                "importance": int(item.importance),
                "project": item.project or "",
                "created_at": item.created_at,
                "last_accessed_at": item.last_accessed_at,
                "source_id": item.source_id or ""
            }
            metadata = _sanitize_metadata(raw_metadata)

            self._initialize()
            assert self._collection is not None

            await asyncio.to_thread(
                self._collection.upsert,
                ids=[item.id],
                embeddings=[embedding],
                documents=[item.text],
                metadatas=[metadata]
            )
            # TODO: Replace with proper logger
            print(f" 💾 [VectorStore] Memory saved ({metadata['category']}): {item.text[:60]}...")
            return True
        except Exception as e:
            # TODO: Replace with proper logger
            print(f"❌ [VectorStore] Error saving memory: {e}")
            return False

    async def search_memories(
        self,
        query: str,
        limit: int = DEFAULT_SEARCH_LIMIT,
        score_threshold: float = DEFAULT_SCORE_THRESHOLD,
        category: Optional[str] = None,
        project: Optional[str] = None
    ) -> List[MemoryItem]:
        """
        Searches for semantically relevant memories with optional metadata filters.
        
        Args:
            query: The search query text.
            limit: Maximum number of results to retrieve.
            score_threshold: Minimum cosine similarity threshold (0.0 to 1.0).
            category: Optional category filter.
            project: Optional project filter.
            
        Returns:
            List[MemoryItem]: Filtered and ranked list of relevant memory items.
        """
        try:
            self._initialize()
            assert self._collection is not None

            # Avoid unnecessary queries if collection is empty
            total_count = await asyncio.to_thread(self._collection.count)
            if total_count == 0:
                return []

            embedding = await self._get_embedding(query)
            if not embedding:
                return []

            # Build metadata filter query
            where_clause: Optional[Where] = None
            conditions: List[Where] = []
            if category:
                conditions.append({"category": category})
            if project:
                conditions.append({"project": project})

            if len(conditions) == 1:
                where_clause = conditions[0]
            elif len(conditions) > 1:
                where_clause = {"$and": conditions}

            actual_limit = min(limit, total_count)

            results = await asyncio.to_thread(
                self._collection.query,
                query_embeddings=[embedding],
                n_results=actual_limit,
                where=where_clause,
                include=["documents", "metadatas", "distances"]
            )

            memories: List[MemoryItem] = []
            if not results or not results.get("ids") or not results["ids"][0]:
                return memories

            ids = results["ids"][0]
            docs = results["documents"][0] if results.get("documents") and results["documents"] else []
            metadatas = results["metadatas"][0] if results.get("metadatas") and results["metadatas"] else []
            distances = results["distances"][0] if results.get("distances") and results["distances"] else []

            now_iso = datetime.now(timezone.utc).isoformat()

            for i in range(len(ids)):
                mem_id = str(ids[i])
                doc = str(docs[i]) if i < len(docs) else ""
                raw_meta = metadatas[i] if i < len(metadatas) and metadatas[i] else {}
                meta: Dict[str, Any] = dict(raw_meta)
                dist = distances[i] if i < len(distances) else 1.0

                # For cosine distance metric: similarity = 1.0 - distance
                similarity = max(0.0, 1.0 - float(dist))

                if similarity >= score_threshold:
                    cat_str = str(meta.get("category", "FACT"))
                    try:
                        cat_enum = MemoryCategory(cat_str)
                    except Exception:
                        cat_enum = MemoryCategory.FACT

                    raw_imp = meta.get("importance", DEFAULT_IMPORTANCE_SCORE)
                    try:
                        imp_val = int(raw_imp) if raw_imp is not None else DEFAULT_IMPORTANCE_SCORE
                    except (ValueError, TypeError):
                        imp_val = DEFAULT_IMPORTANCE_SCORE

                    proj_val = meta.get("project")
                    created_at_val = meta.get("created_at")
                    last_accessed_val = meta.get("last_accessed_at")
                    source_id_val = meta.get("source_id")

                    item = MemoryItem(
                        id=mem_id,
                        text=doc,
                        category=cat_enum,
                        importance=imp_val,
                        project=str(proj_val) if proj_val else None,
                        created_at=str(created_at_val) if created_at_val else now_iso,
                        last_accessed_at=str(last_accessed_val) if last_accessed_val else now_iso,
                        source_id=str(source_id_val) if source_id_val else None,
                        similarity_score=round(similarity, SIMILARITY_PRECISION)
                    )
                    memories.append(item)
                    
                    # Asynchronously refresh last accessed timestamp
                    asyncio.create_task(self.touch_memory(mem_id, meta))

            return memories
        except Exception as e:
            # TODO: Replace with proper logger
            print(f"⚠️ [VectorStore] Error during semantic search: {e}")
            return []

    async def touch_memory(self, memory_id: str, current_metadata: Optional[Mapping[str, Any]] = None) -> None:
        """Updates the last accessed timestamp of a memory item."""
        try:
            self._initialize()
            assert self._collection is not None
            
            meta: Dict[str, Any] = {}
            if current_metadata:
                meta = dict(current_metadata)
            else:
                existing = await asyncio.to_thread(self._collection.get, ids=[memory_id], include=["metadatas"])
                if existing and existing.get("metadatas") and existing["metadatas"]:
                    raw = existing["metadatas"][0] or {}
                    meta = dict(raw)

            meta["last_accessed_at"] = datetime.now(timezone.utc).isoformat()
            clean_meta = _sanitize_metadata(meta)

            await asyncio.to_thread(
                self._collection.update,
                ids=[memory_id],
                metadatas=[clean_meta]
            )
        except Exception:
            # TODO: Replace with proper logger
            pass

    async def update_memory(
        self,
        memory_id: str,
        new_text: str,
        category: Optional[MemoryCategory] = None,
        importance: Optional[int] = None
    ) -> bool:
        """
        Updates the text content, embedding, and metadata of an existing memory.
        
        Returns:
            bool: True if memory was successfully updated, False otherwise.
        """
        try:
            embedding = await self._get_embedding(new_text)
            if not embedding:
                return False

            self._initialize()
            assert self._collection is not None

            existing = await asyncio.to_thread(self._collection.get, ids=[memory_id], include=["metadatas"])
            if not existing or not existing.get("ids") or not existing["ids"]:
                # TODO: Replace with proper logger
                print(f"⚠️ [VectorStore] Memory not found for ID: {memory_id}")
                return False

            raw_meta = existing["metadatas"][0] if existing.get("metadatas") and existing["metadatas"] and existing["metadatas"][0] else {}
            meta: Dict[str, Any] = dict(raw_meta)
            if category:
                meta["category"] = category.value if isinstance(category, MemoryCategory) else str(category)
            if importance is not None:
                meta["importance"] = int(importance)
            meta["last_accessed_at"] = datetime.now(timezone.utc).isoformat()

            clean_meta = _sanitize_metadata(meta)

            await asyncio.to_thread(
                self._collection.update,
                ids=[memory_id],
                documents=[new_text],
                embeddings=[embedding],
                metadatas=[clean_meta]
            )
            # TODO: Replace with proper logger
            print(f" 🔄 [VectorStore] Memory updated (ID: {memory_id[:8]}): {new_text[:50]}...")
            return True
        except Exception as e:
            # TODO: Replace with proper logger
            print(f"❌ [VectorStore] Error updating memory: {e}")
            return False

    async def delete_memory(self, memory_id: str) -> bool:
        """
        Deletes a memory record by its unique ID.
        
        Returns:
            bool: True if deleted successfully, False otherwise.
        """
        try:
            self._initialize()
            assert self._collection is not None
            await asyncio.to_thread(self._collection.delete, ids=[memory_id])
            # TODO: Replace with proper logger
            print(f" 🗑️ [VectorStore] Memory deleted (ID: {memory_id[:8]})")
            return True
        except Exception as e:
            # TODO: Replace with proper logger
            print(f"❌ [VectorStore] Error deleting memory: {e}")
            return False

    def format_for_context(self, memories: Sequence[Any]) -> str:
        """
        Formats retrieved memories into an XML-tagged context block for LLM prompt injection.
        Internal prompt text is kept in Spanish to match agent conversational expectations.
        """
        if not memories:
            return ""

        lines = ["<auxiliary_context>"]
        lines.append("Información relevante recuperada de sesiones anteriores:")
        for mem in memories:
            if isinstance(mem, dict):
                cat_val = mem.get("category", "")
                project = mem.get("project")
                text = mem.get("text", "")
            else:
                if isinstance(mem.category, MemoryCategory):
                    cat_val = mem.category.value
                elif mem.category:
                    cat_val = str(mem.category)
                else:
                    cat_val = ""
                project = getattr(mem, "project", None)
                text = getattr(mem, "text", "")

            cat_label = f"[{cat_val}]" if cat_val else ""
            proj_label = f" (Proyecto: {project})" if project else ""
            lines.append(f"- {cat_label}{proj_label} {text}")
        lines.append("</auxiliary_context>")
        return "\n".join(lines)
