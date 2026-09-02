import re
import json
import asyncio
from typing import List, Dict, Any, Optional, Sequence
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_ollama import ChatOllama

from memory.models import MemoryItem, MemoryCategory, MemoryExtractionPlan, MemoryOperationType
from memory.vector_store import VectorMemoryStore
from memory.profile_store import ProfileStore

# Default asynchronous memory manager parameters
DEFAULT_DEBOUNCE_SECONDS = 45.0
DEFAULT_MODEL_NAME = "qwen2.5:7b"
DEFAULT_TEMPERATURE = 0.1

# Candidate retrieval and deduplication thresholds
CANDIDATE_SEARCH_LIMIT = 5
CANDIDATE_SCORE_THRESHOLD = 0.50
DEDUPLICATION_SCORE_THRESHOLD = 0.85
FALLBACK_UPDATE_SCORE_THRESHOLD = 0.70
FALLBACK_DELETE_SCORE_THRESHOLD = 0.75

# Heuristic filter and key formatting parameters
MIN_NON_TRIVIAL_LENGTH = 10
MAX_PROFILE_KEY_LENGTH = 30

TRIVIAL_PATTERNS = [
    re.compile(r"^(hola|buenas|buenos d[ií]as|buenas tardes|buenas noches|hey|hello|hi)[\s!\.]*$", re.IGNORECASE),
    re.compile(r"^(gracias|muchas gracias|thx|thanks|ty)[\s!\.]*$", re.IGNORECASE),
    re.compile(r"^(ok|vale|de acuerdo|perfecto|entendido|guay|genial|bien|s[ií]|no)[\s!\.]*$", re.IGNORECASE),
    re.compile(r"^(adi[oó]s|hasta luego|chao|bye|nos vemos)[\s!\.]*$", re.IGNORECASE),
    re.compile(r"^(jaja|jajaja|jeje|xd|lol)[\s!\.]*$", re.IGNORECASE),
]

EXTRACTION_PROMPT = """Eres el Gestor de Memoria a Largo Plazo del asistente Jarvis.
Tu misión es analizar el bloque de conversación reciente entre el Usuario y el Asistente, junto con los recuerdos existentes relacionados, para extraer o actualizar información valiosa y persistente que deba recordarse en futuras sesiones.

CRITERIOS ESTRICTOS:
1. INFORMACIÓN A CONSERVAR:
   - Preferencias explícitas o implícitas del usuario (ej: "prefiero respuestas en typescript", "llámame Jose").
   - Información y rutas de proyectos (ej: "estoy trabajando en el proyecto agentic-desktop-assistant", "la API corre en puerto 8080").
   - Decisiones técnicas y arquitectónicas estables.
   - Datos personales o de entorno que el usuario haya revelado y sean útiles.

2. INFORMACIÓN A IGNORAR TOTALMENTE:
   - Saludos, despedidas, agradecimientos o charlas informales.
   - Comandos y resultados de herramientas puntuales (ej: "he matado el proceso 1234", "listado de archivos").
   - Preguntas generales de conocimiento ("¿cuál es la capital de Francia?").
   - Estados momentáneos o efímeros.

3. TIPOS DE OPERACIONES:
   - "CREATE": Hecho nuevo relevante que NO está en la lista de recuerdos existentes (dejar "memory_id": null).
   - "UPDATE": El usuario modifica, contradice o actualiza un recuerdo que YA figura en la lista de recuerdos existentes. Debes incluir obligatoriamente el "memory_id" del recuerdo existente correspondiente y el nuevo "text".
   - "DELETE": El usuario pide olvidar, descarta o invalida expresamente un recuerdo que figura en la lista. Debes incluir obligatoriamente el "memory_id" del recuerdo a eliminar.
   - "NOTHING": Conversación trivial, sin datos persistentes o sin cambios relevantes.

FORMATO DE RESPUESTA REQUERIDO:
Debes responder ÚNICAMENTE con un objeto JSON válido con la clave 'operations', conteniendo una lista de operaciones:
{
  "operations": [
    {
      "op": "CREATE" | "UPDATE" | "DELETE" | "NOTHING",
      "memory_id": "id-del-recuerdo-existente o null",
      "text": "Descripción clara, concisa y atómica del hecho a recordar en tercera persona o formato declarativo (para CREATE o UPDATE)",
      "category": "PREFERENCE" | "PROJECT" | "SYSTEM_CONFIG" | "DECISION" | "FACT",
      "importance": 1 a 5,
      "project": "nombre del proyecto o null",
      "reason": "breve justificación"
    }
  ]
}
Si no hay nada relevante que recordar ni actualizar, devuelve: {"operations": [{"op": "NOTHING", "reason": "Conversación trivial o sin cambios persistentes"}]}
Responde SOLO con el JSON, sin bloques de markdown adicionales."""


def _clean_json_markdown(raw_text: str) -> str:
    """Strips markdown code block wrappers from a raw JSON string."""
    cleaned = raw_text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return cleaned.strip()


def _derive_preference_key(text: str, max_length: int = MAX_PROFILE_KEY_LENGTH) -> Optional[str]:
    """Generates a sanitized slug key suitable for SQLite profile storage from preference text."""
    key_clean = re.sub(r'[^a-zA-Z0-9_]', '_', text[:max_length]).strip('_').lower()
    return f"pref_{key_clean}" if key_clean else None


class AsyncMemoryManager:
    """
    Level 3 Memory: Asynchronous Background Memory Lifecycle Manager.
    
    Implements a zero-contention background architecture using:
    - Activity-based debounce cooldown timers.
    - Conversational turn batching.
    - Zero-cost heuristic pre-LLM filtering.
    - Pre-extraction contextual retrieval (RAG).
    - Full semantic CRUD lifecycle (Create, Update, Delete, Deduplicate).
    """

    def __init__(
        self,
        vector_store: VectorMemoryStore,
        profile_store: ProfileStore,
        model_name: str = DEFAULT_MODEL_NAME,
        debounce_seconds: float = DEFAULT_DEBOUNCE_SECONDS,
        temperature: float = DEFAULT_TEMPERATURE
    ) -> None:
        """
        Initializes the asynchronous memory manager.

        Args:
            vector_store: Semantic vector database interface.
            profile_store: Structured profile key-value storage interface.
            model_name: Ollama model identifier for extraction tasks.
            debounce_seconds: Inactivity delay before processing accumulated dialogue.
            temperature: Sampling temperature for deterministic extraction.
        """
        self.vector_store = vector_store
        self.profile_store = profile_store
        self.llm = ChatOllama(model=model_name, temperature=temperature)
        self.debounce_seconds = debounce_seconds
        
        self._pending_turns: List[Dict[str, str]] = []
        self._debounce_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        self._is_processing = False

    def record_turn(self, role: str, content: str) -> None:
        """
        Appends a dialogue turn to the pending buffer and resets the inactivity cooldown timer.

        Args:
            role: Speaker role ('user' or 'assistant').
            content: Raw conversational text.
        """
        if not content or not content.strip():
            return

        self._pending_turns.append({"role": role, "content": content.strip()})
        
        # Reset cooldown timer on incoming activity
        if self._debounce_task and not self._debounce_task.done():
            self._debounce_task.cancel()

        self._debounce_task = asyncio.create_task(self._debounce_cooldown())

    async def _debounce_cooldown(self) -> None:
        """
        Waits for the configured inactivity window before triggering batch processing.
        Handles task cancellation when subsequent messages arrive during cooldown.
        """
        try:
            await asyncio.sleep(self.debounce_seconds)
            await self._process_pending_buffer()
        except asyncio.CancelledError:
            # Cancelled due to incoming user message during cooldown window
            pass
        except Exception as e:
            # TODO: Replace with proper logger
            print(f"⚠️ [AsyncMemoryManager] Debounce cooldown error: {e}")

    def _is_trivial_block(self, turns: Sequence[Dict[str, str]]) -> bool:
        """
        Zero-cost heuristic pre-filter to detect trivial conversational turns.
        Avoids redundant LLM invocations for routine greetings, acknowledgements, or short replies.

        Args:
            turns: List of conversational turn dictionaries with 'role' and 'content'.

        Returns:
            bool: True if the conversation block contains no substantial facts, False otherwise.
        """
        user_texts = [t["content"].lower().strip() for t in turns if t.get("role") == "user" and t.get("content")]
        if not user_texts:
            return True

        for text in user_texts:
            is_trivial = any(pat.match(text) for pat in TRIVIAL_PATTERNS)
            if not is_trivial and len(text) > MIN_NON_TRIVIAL_LENGTH:
                return False

        return True

    async def _process_pending_buffer(self) -> None:
        """
        Processes accumulated conversation turns from the pending queue.
        Applies heuristic filtering, retrieves candidate context, invokes the extractor LLM,
        and dispatches state updates.
        """
        async with self._lock:
            if not self._pending_turns:
                return

            turns_to_process = list(self._pending_turns)
            self._pending_turns.clear()

        # Step 1: Zero-cost heuristic pre-filter
        if self._is_trivial_block(turns_to_process):
            return

        self._is_processing = True
        try:
            formatted_dialogue = [
                f"{'Usuario' if t['role'] == 'user' else 'Asistente'}: {t['content']}" 
                for t in turns_to_process
            ]
            user_messages = [t["content"] for t in turns_to_process if t.get("role") == "user" and t.get("content")]

            dialogue_text = "\n".join(formatted_dialogue)
            user_query = " ".join(user_messages)

            # Step 2: Retrieve potentially related existing memories for context
            existing_memories = await self.vector_store.search_memories(
                query=user_query or dialogue_text,
                limit=CANDIDATE_SEARCH_LIMIT,
                score_threshold=CANDIDATE_SCORE_THRESHOLD
            )

            # Step 3: Format existing memories with unique IDs for LLM referencing
            if existing_memories:
                memories_context_lines = ["Recuerdos existentes relacionados en memoria:"]
                for m in existing_memories:
                    proj_info = f" [Proyecto: {m.project}]" if m.project else ""
                    memories_context_lines.append(f"- [ID: {m.id}] ({m.category.value}){proj_info} {m.text}")
                memories_context = "\n".join(memories_context_lines)
            else:
                memories_context = "Recuerdos existentes relacionados en memoria:\n(Ninguno encontrado)"

            messages = [
                SystemMessage(content=EXTRACTION_PROMPT),
                HumanMessage(content=f"{memories_context}\n\nBloque de conversación a analizar:\n{dialogue_text}")
            ]

            # TODO: Replace with proper logger
            print(" 🧠 [AsyncMemoryManager] Analyzing conversation batch with memory context...")
            response = await self.llm.ainvoke(messages)
            raw_content = response.content if isinstance(response.content, str) else ""

            await self._apply_memory_operations(raw_content)

        except Exception as e:
            # TODO: Replace with proper logger
            print(f"❌ [AsyncMemoryManager] Error processing memory extraction: {e}")
        finally:
            self._is_processing = False

    async def _apply_memory_operations(self, raw_json_text: str) -> None:
        """
        Parses LLM extraction plan output and applies database operations to VectorStore and ProfileStore.

        Args:
            raw_json_text: Raw response string from the extraction LLM containing JSON operations.
        """
        cleaned = _clean_json_markdown(raw_json_text)

        try:
            data = json.loads(cleaned)
            # Normalize operation keys to uppercase defensively before validation
            if isinstance(data, dict) and "operations" in data and isinstance(data["operations"], list):
                for item in data["operations"]:
                    if isinstance(item, dict) and "op" in item and isinstance(item["op"], str):
                        item["op"] = item["op"].upper()
            plan = MemoryExtractionPlan.model_validate(data)
            operations = plan.operations
        except Exception as parse_err:
            # TODO: Replace with proper logger
            print(f"⚠️ [AsyncMemoryManager] Failed to parse memory extraction JSON plan: {parse_err}")
            return

        for op_item in operations:
            op = op_item.op
            text = (op_item.text or "").strip()
            category = op_item.category or MemoryCategory.FACT
            importance = op_item.importance if op_item.importance is not None else 3
            project = op_item.project
            mem_id = op_item.memory_id

            if op == MemoryOperationType.NOTHING:
                continue

            if op != MemoryOperationType.DELETE and not text:
                continue

            if op == MemoryOperationType.CREATE:
                # Deduplication check against vector store
                existing = await self.vector_store.search_memories(
                    query=text,
                    limit=1,
                    score_threshold=DEDUPLICATION_SCORE_THRESHOLD
                )

                if existing:
                    target_id = existing[0].id
                    await self.vector_store.update_memory(
                        memory_id=target_id,
                        new_text=text,
                        category=category,
                        importance=importance
                    )
                else:
                    item = MemoryItem(
                        text=text,
                        category=category,
                        importance=importance,
                        project=project
                    )
                    await self.vector_store.add_memory(item)

                if category == MemoryCategory.PREFERENCE:
                    pref_key = _derive_preference_key(text)
                    if pref_key:
                        await self.profile_store.set(pref_key, text, category="preferences")

            elif op == MemoryOperationType.UPDATE:
                if mem_id:
                    await self.vector_store.update_memory(
                        memory_id=mem_id,
                        new_text=text,
                        category=category,
                        importance=importance
                    )
                else:
                    # Fallback if LLM omitted memory_id: search for semantic match
                    existing = await self.vector_store.search_memories(
                        query=text,
                        limit=1,
                        score_threshold=FALLBACK_UPDATE_SCORE_THRESHOLD
                    )
                    if existing:
                        await self.vector_store.update_memory(
                            memory_id=existing[0].id,
                            new_text=text,
                            category=category,
                            importance=importance
                        )
                    else:
                        item = MemoryItem(
                            text=text,
                            category=category,
                            importance=importance,
                            project=project
                        )
                        await self.vector_store.add_memory(item)

                if category == MemoryCategory.PREFERENCE:
                    pref_key = _derive_preference_key(text)
                    if pref_key:
                        await self.profile_store.set(pref_key, text, category="preferences")

            elif op == MemoryOperationType.DELETE:
                if mem_id:
                    await self.vector_store.delete_memory(mem_id)
                elif text:
                    existing = await self.vector_store.search_memories(
                        query=text,
                        limit=1,
                        score_threshold=FALLBACK_DELETE_SCORE_THRESHOLD
                    )
                    if existing:
                        await self.vector_store.delete_memory(existing[0].id)

    async def flush_and_close(self) -> None:
        """
        Forces immediate execution of pending buffered turns during graceful service termination.
        """
        if self._debounce_task and not self._debounce_task.done():
            self._debounce_task.cancel()
        
        if self._pending_turns:
            # TODO: Replace with proper logger
            print(" 🔄 [AsyncMemoryManager] Flushing pending memories before shutdown...")
            await self._process_pending_buffer()
