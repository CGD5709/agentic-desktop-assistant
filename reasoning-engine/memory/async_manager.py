import re
import json
import asyncio
from typing import List, Dict, Any, Optional
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_ollama import ChatOllama

from memory.models import MemoryItem, MemoryCategory, MemoryExtractionPlan, MemoryOperationType
from memory.vector_store import VectorMemoryStore
from memory.profile_store import ProfileStore


TRIVIAL_PATTERNS = [
    r"^(hola|buenas|buenos d[ií]as|buenas tardes|buenas noches|hey|hello|hi)[\s!\.]*$",
    r"^(gracias|muchas gracias|thx|thanks|ty)[\s!\.]*$",
    r"^(ok|vale|de acuerdo|perfecto|entendido|guay|genial|bien|s[ií]|no)[\s!\.]*$",
    r"^(adi[oó]s|hasta luego|chao|bye|nos vemos)[\s!\.]*$",
    r"^(jaja|jajaja|jeje|xd|lol)[\s!\.]*$",
]

EXTRACTION_PROMPT = """Eres el Gestor de Memoria a Largo Plazo del asistente Jarvis.
Tu misión es analizar el bloque de conversación reciente entre el Usuario y el Asistente para extraer información valiosa y persistente que deba recordarse en futuras sesiones.

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

FORMATO DE RESPUESTA REQUERIDO:
Debes responder ÚNICAMENTE con un objeto JSON válido con la clave 'operations', conteniendo una lista de operaciones:
{
  "operations": [
    {
      "op": "CREATE" | "UPDATE" | "DELETE" | "NOTHING",
      "text": "Descripción clara, concisa y atómica del hecho a recordar en tercera persona o formato declarativo",
      "category": "PREFERENCE" | "PROJECT" | "SYSTEM_CONFIG" | "DECISION" | "FACT",
      "importance": 1 a 5,
      "project": "nombre del proyecto o null",
      "reason": "breve justificación"
    }
  ]
}
Si no hay nada relevante que recordar, devuelve: {"operations": [{"op": "NOTHING", "reason": "Conversación trivial o sin datos persistentes"}]}
Responde SOLO con el JSON, sin bloques de markdown adicionales."""


class AsyncMemoryManager:
    """
    Nivel 3: Gestor Asíncrono de Memoria en Background.
    Implementa la estrategia Zero-Contention mediante:
    - Cooldown / Debounce por inactividad (45s por defecto).
    - Batching de turnos acumulados.
    - Filtro heurístico pre-LLM sin coste computacional.
    - Deduplicación semántica previa a la creación.
    """

    def __init__(
        self,
        vector_store: VectorMemoryStore,
        profile_store: ProfileStore,
        model_name: str = "qwen2.5:7b",
        debounce_seconds: float = 45.0,
        temperature: float = 0.1
    ):
        self.vector_store = vector_store
        self.profile_store = profile_store
        self.llm = ChatOllama(model=model_name, temperature=temperature)
        self.debounce_seconds = debounce_seconds
        
        self._pending_turns: List[Dict[str, str]] = []
        self._debounce_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        self._is_processing = False

    def record_turn(self, role: str, content: str):
        """Registra un turno de conversación y reinicia el temporizador de inactividad."""
        if not content or not content.strip():
            return

        self._pending_turns.append({"role": role, "content": content.strip()})
        
        # Reiniciamos el temporizador de debounce
        if self._debounce_task and not self._debounce_task.done():
            self._debounce_task.cancel()

        self._debounce_task = asyncio.create_task(self._debounce_cooldown())

    async def _debounce_cooldown(self):
        """Espera el periodo de inactividad antes de procesar el lote."""
        try:
            await asyncio.sleep(self.debounce_seconds)
            await self._process_pending_buffer()
        except asyncio.CancelledError:
            # Cancelado porque el usuario envió otro mensaje antes de que expirara el cooldown
            pass
        except Exception as e:
            print(f"⚠️ [AsyncMemoryManager] Error en cooldown de memoria: {e}")

    def _is_trivial_block(self, turns: List[Dict[str, str]]) -> bool:
        """Filtro Heurístico Pre-LLM (Zero-Cost)."""
        user_texts = [t["content"].lower().strip() for t in turns if t["role"] == "user"]
        if not user_texts:
            return True

        # Si todos los mensajes de usuario son triviales
        for text in user_texts:
            is_trivial = False
            for pat in TRIVIAL_PATTERNS:
                if re.match(pat, text, re.IGNORECASE):
                    is_trivial = True
                    break
            if not is_trivial and len(text) > 10:
                # Hay al menos un mensaje no trivial con longitud suficiente
                return False

        return True

    async def _process_pending_buffer(self):
        """Procesa el bloque acumulado de turnos."""
        async with self._lock:
            if not self._pending_turns:
                return

            turns_to_process = list(self._pending_turns)
            self._pending_turns.clear()

        # 1. Filtro Heurístico Pre-LLM
        if self._is_trivial_block(turns_to_process):
            # Descarte a coste 0 sin gastar inferencia
            return

        self._is_processing = True
        try:
            formatted_dialogue = []
            for t in turns_to_process:
                role_tag = "Usuario" if t["role"] == "user" else "Jarvis"
                formatted_dialogue.append(f"{role_tag}: {t['content']}")

            dialogue_text = "\n".join(formatted_dialogue)

            messages = [
                SystemMessage(content=EXTRACTION_PROMPT),
                HumanMessage(content=f"Analiza este bloque de conversación:\n\n{dialogue_text}")
            ]

            print(" 🧠 [AsyncMemoryManager] Analizando bloque de conversación en segundo plano...")
            response = await self.llm.ainvoke(messages)
            raw_content = response.content if isinstance(response.content, str) else ""

            await self._apply_memory_operations(raw_content)

        except Exception as e:
            print(f"❌ [AsyncMemoryManager] Error procesando extracción de memoria: {e}")
        finally:
            self._is_processing = False

    async def _apply_memory_operations(self, raw_json_text: str):
        """Parsea la salida del LLM y ejecuta las operaciones en VectorStore y ProfileStore."""
        # Limpieza básica de formato Markdown si el LLM incluye ```json
        cleaned = raw_json_text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            data = json.loads(cleaned)
            operations = data.get("operations", [])
        except Exception as parse_err:
            print(f"⚠️ [AsyncMemoryManager] No se pudo parsear el plan de memoria JSON: {parse_err}")
            return

        for op_data in operations:
            op = op_data.get("op", "NOTHING").upper()
            text = op_data.get("text", "")
            cat_str = op_data.get("category", "FACT")
            importance = op_data.get("importance", 3)
            project = op_data.get("project")

            if op == "NOTHING" or not text:
                continue

            try:
                category = MemoryCategory(cat_str)
            except Exception:
                category = MemoryCategory.FACT

            if op == "CREATE":
                # Comprobación de deduplicación previa
                existing = await self.vector_store.search_memories(
                    query=text,
                    limit=1,
                    score_threshold=0.85
                )

                if existing:
                    # Si ya existe algo muy similar, actualizamos en vez de duplicar
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

                # Si es una preferencia de perfil clave, la guardamos también en ProfileStore
                if category == MemoryCategory.PREFERENCE:
                    key_clean = re.sub(r'[^a-zA-Z0-9_]', '_', text[:30]).strip('_').lower()
                    if key_clean:
                        await self.profile_store.set(f"pref_{key_clean}", text, category="preferences")

            elif op == "UPDATE":
                mem_id = op_data.get("memory_id")
                if mem_id:
                    await self.vector_store.update_memory(
                        memory_id=mem_id,
                        new_text=text,
                        category=category,
                        importance=importance
                    )

            elif op == "DELETE":
                mem_id = op_data.get("memory_id")
                if mem_id:
                    await self.vector_store.delete_memory(mem_id)

    async def flush_and_close(self):
        """Fuerza el procesamiento inmediato de turnos pendientes al apagar el servicio."""
        if self._debounce_task and not self._debounce_task.done():
            self._debounce_task.cancel()
        
        if self._pending_turns:
            print(" 🔄 [AsyncMemoryManager] Procesando memorias pendientes antes de cerrar...")
            await self._process_pending_buffer()
