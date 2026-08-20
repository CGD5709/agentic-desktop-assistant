import os
import asyncio
from typing import List, Optional, Dict, Any, Sequence
from datetime import datetime, timezone
import chromadb
from langchain_ollama import OllamaEmbeddings
from memory.models import MemoryItem, MemoryCategory


def _sanitize_metadata(raw_meta: Dict[str, Any]) -> Dict[str, Any]:
    """
    ChromaDB solo admite str, int, float y bool como valores de metadatos.
    Convierte valores None o tipos complejos a representaciones compatibles.
    """
    clean = {}
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
    Nivel 2: Memoria a Largo Plazo Semántica (RAG)
    Almacena recuerdos relevantes entre sesiones en una base de datos vectorial ChromaDB local,
    utilizando el modelo de embeddings nomic-embed-text ejecutado en Ollama.
    """

    def __init__(
        self,
        persist_directory: str = "./data/chroma_db",
        collection_name: str = "jarvis_long_term_memory",
        embedding_model: str = "nomic-embed-text",
        ollama_base_url: str = "http://localhost:11434"
    ):
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        self.ollama_base_url = ollama_base_url
        self._client: Optional[chromadb.PersistentClient] = None
        self._collection = None
        self._embeddings: Optional[OllamaEmbeddings] = None

    def _initialize(self):
        """Inicializa ChromaDB y la colección localmente de forma síncrona/lazy."""
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

    async def initialize(self):
        """Inicialización asíncrona no bloqueante."""
        await asyncio.to_thread(self._initialize)

    async def _get_embedding(self, text: str) -> List[float]:
        self._initialize()
        assert self._embeddings is not None
        try:
            return await asyncio.to_thread(self._embeddings.embed_query, text)
        except Exception as e:
            print(f"⚠️ [VectorStore] Error al generar embedding con Ollama ({self.embedding_model}): {e}")
            return []

    async def add_memory(self, item: MemoryItem) -> bool:
        """Añade un nuevo recuerdo con embedding y metadatos estructurados."""
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
            print(f" 💾 [VectorStore] Memoria guardada ({metadata['category']}): {item.text[:60]}...")
            return True
        except Exception as e:
            print(f"❌ [VectorStore] Error guardando memoria: {e}")
            return False

    async def search_memories(
        self,
        query: str,
        limit: int = 4,
        score_threshold: float = 0.65,
        category: Optional[str] = None,
        project: Optional[str] = None
    ) -> List[MemoryItem]:
        """
        Busca recuerdos semánticamente relevantes aplicando umbral de similitud
        y filtros de metadatos opcionales.
        """
        try:
            self._initialize()
            assert self._collection is not None

            # Si la base de datos está vacía, evitamos consulta innecesaria
            total_count = await asyncio.to_thread(self._collection.count)
            if total_count == 0:
                return []

            embedding = await self._get_embedding(query)
            if not embedding:
                return []

            where_clause: Optional[Dict[str, Any]] = None
            conditions = []
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
                mem_id = ids[i]
                doc = docs[i] if i < len(docs) else ""
                meta = metadatas[i] if i < len(metadatas) and metadatas[i] else {}
                dist = distances[i] if i < len(distances) else 1.0

                # Para distancia coseno: similitud = 1 - distancia
                similarity = max(0.0, 1.0 - float(dist))

                if similarity >= score_threshold:
                    cat_str = meta.get("category", "FACT")
                    try:
                        cat_enum = MemoryCategory(cat_str)
                    except Exception:
                        cat_enum = MemoryCategory.FACT

                    item = MemoryItem(
                        id=mem_id,
                        text=doc,
                        category=cat_enum,
                        importance=int(meta.get("importance", 3)),
                        project=meta.get("project") or None,
                        created_at=meta.get("created_at", now_iso),
                        last_accessed_at=meta.get("last_accessed_at", now_iso),
                        source_id=meta.get("source_id") or None,
                        similarity_score=round(similarity, 3)
                    )
                    memories.append(item)
                    
                    # Actualizamos asíncronamente el último acceso
                    asyncio.create_task(self.touch_memory(mem_id, meta))

            return memories
        except Exception as e:
            print(f"⚠️ [VectorStore] Error en búsqueda semántica: {e}")
            return []

    async def touch_memory(self, memory_id: str, current_metadata: Optional[Dict[str, Any]] = None):
        """Actualiza la fecha de último acceso de un recuerdo."""
        try:
            self._initialize()
            assert self._collection is not None
            
            if current_metadata:
                meta = dict(current_metadata)
            else:
                existing = await asyncio.to_thread(self._collection.get, ids=[memory_id], include=["metadatas"])
                if existing and existing.get("metadatas") and existing["metadatas"]:
                    meta = existing["metadatas"][0] or {}
                else:
                    meta = {}

            meta["last_accessed_at"] = datetime.now(timezone.utc).isoformat()
            clean_meta = _sanitize_metadata(meta)

            await asyncio.to_thread(
                self._collection.update,
                ids=[memory_id],
                metadatas=[clean_meta]
            )
        except Exception:
            pass

    async def update_memory(
        self,
        memory_id: str,
        new_text: str,
        category: Optional[MemoryCategory] = None,
        importance: Optional[int] = None
    ) -> bool:
        """Actualiza el contenido y embedding de un recuerdo existente."""
        try:
            embedding = await self._get_embedding(new_text)
            if not embedding:
                return False

            self._initialize()
            assert self._collection is not None

            existing = await asyncio.to_thread(self._collection.get, ids=[memory_id], include=["metadatas"])
            if not existing or not existing.get("ids") or not existing["ids"]:
                print(f"⚠️ [VectorStore] No se encontró la memoria con ID: {memory_id}")
                return False

            meta = existing["metadatas"][0] if existing.get("metadatas") and existing["metadatas"] and existing["metadatas"][0] else {}
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
            print(f" 🔄 [VectorStore] Memoria actualizada (ID: {memory_id[:8]}): {new_text[:50]}...")
            return True
        except Exception as e:
            print(f"❌ [VectorStore] Error actualizando memoria: {e}")
            return False

    async def delete_memory(self, memory_id: str) -> bool:
        """Elimina una memoria por ID."""
        try:
            self._initialize()
            assert self._collection is not None
            await asyncio.to_thread(self._collection.delete, ids=[memory_id])
            print(f" 🗑️ [VectorStore] Memoria eliminada (ID: {memory_id[:8]})")
            return True
        except Exception as e:
            print(f"❌ [VectorStore] Error eliminando memoria: {e}")
            return False

    def format_for_context(self, memories: Sequence[Any]) -> str:
        """Formatea los recuerdos recuperados como contexto auxiliar explícito."""
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
