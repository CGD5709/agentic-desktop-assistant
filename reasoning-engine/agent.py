from typing import Annotated, Sequence, Literal, List, Dict, Any, Optional, TypedDict
import operator
import time
import uuid
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage
from langgraph.graph import StateGraph, START, END

from langchain_ollama import ChatOllama
from rabbitmq import RabbitMQClient
from models import EventEnvelope, EventMetadata, EventType, ToolExecutionRequestPayload

from memory.models import MemoryItem
from memory.profile_store import ProfileStore
from memory.vector_store import VectorMemoryStore
from memory.async_manager import AsyncMemoryManager
from memory.short_term import SessionSummarizer, trim_messages_token_budget
from memory.context_assembler import ContextAssembler

# === CLIENTES Y ALMACENES GLOBALES ===
mq_client = RabbitMQClient()
profile_store = ProfileStore(db_path="./data/assistant_profile.db")
vector_store = VectorMemoryStore(persist_directory="./data/chroma_db")
memory_manager = AsyncMemoryManager(
    vector_store=vector_store,
    profile_store=profile_store,
    debounce_seconds=45.0
)
session_summarizer = SessionSummarizer()

# Herramientas dinámicas registradas desde Java (formato OpenAI)
dynamic_tools: List[Dict[str, Any]] = []

# Modelo optimizado para function calling y razonamiento local (Qwen 2.5 7B)
llm = ChatOllama(model="qwen2.5:7b", temperature=0.2)

# === ESTADO DEL GRAFO ===
class AgentState(TypedDict, total=False):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    intent: Optional[str]
    correlation_id: Optional[str]
    retrieved_memories: Optional[List[Dict[str, Any]]]

# === SYSTEM PROMPTS ===
JARVIS_SYSTEM_PROMPT = """Eres Jarvis, un asistente de escritorio inteligente, sofisticado, leal y eficiente.
Tu propósito es ayudar al usuario de forma natural, ingeniosa y clara.
Mantén tus respuestas conversacionales concisas, amables y elegantes.

REGLA CRÍTICA DE VERACIDAD:
NUNCA inventes métricas del sistema operativo, procesos en ejecución, uso de memoria/CPU, puertos ni finjas haber ejecutado diagnósticos o acciones en el PC si no dispones de los datos reales devueltos por una herramienta."""

ROUTER_PROMPT = """Eres el clasificador de intenciones para el asistente de escritorio Jarvis.
Tu ÚNICA tarea es clasificar el último mensaje del usuario en una de estas dos categorías:

- CHAT: Saludos ("hola"), agradecimientos ("gracias"), despedidas ("adiós"), charla informal, bromas, preguntas teóricas o de cultura general ("¿qué es la fotosíntesis?"), donde NO se interactúa ni se consulta el estado del ordenador.
- COMMAND: El usuario pide realizar una acción técnica O consultar el estado/diagnóstico en tiempo real del ordenador.
  Ejemplos de COMMAND:
  * Consultas de estado del sistema, consumo de recursos, memoria RAM, CPU, disco (ej: "qué procesos consumen más memoria", "dime el rendimiento", "cuánta RAM tengo libre").
  * Gestión de procesos y ventanas (ej: "cierra chrome", "mata el proceso X", "qué aplicaciones están abiertas").
  * Red y seguridad (ej: "escanea los puertos", "mira las conexiones").
  * Abrir webs, lanzar comandos o cualquier interacción con el sistema operativo.

IMPORTANTE: Responde ÚNICAMENTE con la palabra exacta 'CHAT' o 'COMMAND', sin comillas, sin explicaciones y sin formato adicional."""

def extract_last_human_text(messages: Sequence[BaseMessage]) -> str:
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            if isinstance(msg.content, str):
                return msg.content
            elif isinstance(msg.content, list):
                return " ".join(c if isinstance(c, str) else "" for c in msg.content)
    return ""

def is_simple_greeting_or_trivial(text: str) -> bool:
    t = text.strip().lower()
    trivial = {"hola", "buenas", "buenos días", "buenas tardes", "buenas noches", "hey", "hi", "gracias", "adiós", "chao", "bye", "ok", "vale", "jaja"}
    return t in trivial or len(t) < 4

# === 1. NODO ROUTER (Clasificador Semántico de Intenciones y Recuperador RAG) ===
async def router_node(state: AgentState):
    """
    Determina si el usuario quiere charlar o si está dando una orden técnica.
    Si la consulta no es trivial, recupera recuerdos relevantes de ChromaDB (Nivel 2).
    """
    messages = list(state.get("messages", []))
    last_human_text = extract_last_human_text(messages)

    if not last_human_text.strip():
        return {"intent": "CHAT", "retrieved_memories": []}

    # Clasificación de intención CHAT vs COMMAND
    classification_messages = [
        SystemMessage(content=ROUTER_PROMPT),
        HumanMessage(content=f"Mensaje del usuario: {last_human_text}")
    ]
    
    classification = await llm.ainvoke(classification_messages)
    decision = classification.content.strip().upper() if isinstance(classification.content, str) else "CHAT"
    intent = "COMMAND" if "COMMAND" in decision else "CHAT"

    # Recuperación Semántica Condicional (Nivel 2)
    retrieved_memories: List[Dict[str, Any]] = []
    if not is_simple_greeting_or_trivial(last_human_text):
        raw_memories = await vector_store.search_memories(
            query=last_human_text,
            limit=3,
            score_threshold=0.60
        )
        retrieved_memories = [m.model_dump(mode="json") for m in raw_memories]

    return {
        "intent": intent,
        "retrieved_memories": retrieved_memories
    }

# === 2. NODO CHAT (Conversación contextual ensamblada) ===
async def chat_node(state: AgentState):
    """
    Maneja la conversación general de Jarvis ensamblando el contexto de 4 niveles
    (System Prompt, Perfil SQLite, Recuerdos RAG, Resumen y recorte de ~3000 tokens).
    """
    messages = list(state.get("messages", []))
    retrieved_memories = state.get("retrieved_memories") or []
    
    # Nivel 0: Perfil
    profile_ctx = await profile_store.format_for_context()
    # Nivel 1: Resumen
    summary_ctx = session_summarizer.get_summary_context()

    # Ensamblaje limpio de contexto
    assembled_messages = ContextAssembler.assemble(
        base_system_prompt=JARVIS_SYSTEM_PROMPT,
        messages=messages,
        profile_context=profile_ctx,
        retrieved_memories=retrieved_memories,
        session_summary_context=summary_ctx,
        max_dialogue_tokens=3000,
        memory_store_formatter=vector_store.format_for_context
    )

    response = await llm.ainvoke(assembled_messages)
    
    # Registramos en background para el gestor asíncrono (Nivel 3)
    last_human_text = extract_last_human_text(messages)
    assistant_text = response.content if isinstance(response.content, str) else ""
    memory_manager.record_turn(role="user", content=last_human_text)
    memory_manager.record_turn(role="assistant", content=assistant_text)

    return {"messages": [response]}

# === 3. NODO COMMAND (Agente con herramientas vinculadas y contexto de memoria) ===
async def command_node(state: AgentState):
    """
    Maneja comandos técnicos y llamadas a herramientas con contexto completo y control de tokens.
    """
    messages = list(state.get("messages", []))
    retrieved_memories = state.get("retrieved_memories") or []

    profile_ctx = await profile_store.format_for_context()
    summary_ctx = session_summarizer.get_summary_context()

    command_instruction = (
        f"{JARVIS_SYSTEM_PROMPT}\n"
        "El usuario te ha solicitado una orden técnica o una consulta sobre el estado del sistema/ordenador. "
        "Utiliza obligatoriamente las herramientas disponibles adecuadas con los parámetros correctos para obtener los datos reales o cumplir su solicitud. "
        "No respondas con datos inventados sin antes ejecutar la herramienta correspondiente."
    )

    assembled_messages = ContextAssembler.assemble(
        base_system_prompt=command_instruction,
        messages=messages,
        profile_context=profile_ctx,
        retrieved_memories=retrieved_memories,
        session_summary_context=summary_ctx,
        max_dialogue_tokens=3000,
        memory_store_formatter=vector_store.format_for_context
    )

    if dynamic_tools:
        llm_with_tools = llm.bind_tools(dynamic_tools)
        response = await llm_with_tools.ainvoke(assembled_messages)
    else:
        response = await llm.ainvoke(assembled_messages)

    # Si no requiere tools, registramos el turno
    if not (isinstance(response, AIMessage) and response.tool_calls):
        last_human_text = extract_last_human_text(messages)
        assistant_text = response.content if isinstance(response.content, str) else ""
        memory_manager.record_turn(role="user", content=last_human_text)
        memory_manager.record_turn(role="assistant", content=assistant_text)

    return {"messages": [response]}

# === 4. NODO DE ACCIÓN (Ejecución RPC sobre RabbitMQ) ===
async def action_node(state: AgentState):
    """
    Envía la petición de tool call a execution-service vía RabbitMQ y espera la respuesta
    de forma asíncrona y sincronizada (sin límite arbitrario de tiempo).
    """
    last_message = state["messages"][-1]
    assert isinstance(last_message, AIMessage)

    tool_messages: List[ToolMessage] = []

    for tool_call in last_message.tool_calls:
        tool_name = tool_call['name']
        tool_args = tool_call['args']
        tool_call_id = tool_call.get("id") or str(uuid.uuid4())

        request_payload = ToolExecutionRequestPayload(toolName=tool_name, arguments=tool_args)
        envelope = EventEnvelope(
            metadata=EventMetadata(
                eventId=str(uuid.uuid4()),
                correlationId=str(tool_call_id),
                timestamp=int(time.time() * 1000),
                source="reasoning-engine",
                eventType=EventType.EXECUTION_REQUEST
            ),
            payload=request_payload.model_dump(by_alias=True)
        )

        routing_key = f"tool.request.{tool_name}"
        print(f" 🚀 [RabbitMQ] Petición lanzada para: {tool_name}")

        # Esperamos la respuesta de execution-service sin límite de tiempo
        raw_response = await mq_client.send_and_wait(routing_key, envelope)

        payload = raw_response.get("payload", {})
        status = payload.get("status", "SUCCESS")
        output = payload.get("output", "Acción completada.")

        resultado_texto = output if status == "SUCCESS" else f"Error: {output}"
        tool_messages.append(ToolMessage(
            content=resultado_texto,
            tool_call_id=tool_call_id
        ))

    return {"messages": tool_messages}

# === 5. NODO DE RESUMEN (traduce resultados técnicos a Jarvis) ===
async def summarize_node(state: AgentState):
    """
    Toma el resultado técnico de la herramienta y genera una respuesta
    natural y elegante de Jarvis para el usuario.
    """
    messages = list(state["messages"])
    retrieved_memories = state.get("retrieved_memories") or []

    profile_ctx = await profile_store.format_for_context()
    summary_ctx = session_summarizer.get_summary_context()

    summary_instruction = (
        f"{JARVIS_SYSTEM_PROMPT}\n"
        "Acabas de ejecutar la acción solicitada por el usuario en el ordenador y ya tienes el resultado. "
        "Responde al usuario confirmando de forma BREVE, NATURAL y ELEGANTE qué se ha hecho. "
        "No repitas códigos de error ni términos técnicos a menos que sean necesarios."
    )

    assembled_messages = ContextAssembler.assemble(
        base_system_prompt=summary_instruction,
        messages=messages,
        profile_context=profile_ctx,
        retrieved_memories=retrieved_memories,
        session_summary_context=summary_ctx,
        max_dialogue_tokens=3000,
        memory_store_formatter=vector_store.format_for_context
    )

    response = await llm.ainvoke(assembled_messages)

    # Registramos el turno técnico completado para el gestor asíncrono (Nivel 3)
    last_human_text = extract_last_human_text(messages)
    assistant_text = response.content if isinstance(response.content, str) else ""
    memory_manager.record_turn(role="user", content=last_human_text)
    memory_manager.record_turn(role="assistant", content=assistant_text)

    return {"messages": [response]}

# === ENRUTADORES CONDICIONALES ===
def route_intent(state: AgentState) -> Literal["chat_node", "command_node"]:
    if state.get("intent") == "COMMAND":
        return "command_node"
    return "chat_node"

def should_use_tools(state: AgentState) -> Literal["action_node", "end"]:
    last_message = state["messages"][-1]
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "action_node"
    return "end"

# === CONSTRUCCIÓN DEL GRAFO ===
builder = StateGraph(AgentState)  # type: ignore[type-var]

builder.add_node("router_node", router_node)
builder.add_node("chat_node", chat_node)
builder.add_node("command_node", command_node)
builder.add_node("action_node", action_node)
builder.add_node("summarize_node", summarize_node)

# Flujo del Grafo:
# START -> router_node (clasifica intención y recupera RAG si procede)
#           ├─ (CHAT) ────> chat_node ───────────────────────────────> END
#           └─ (COMMAND) ─> command_node ─┬─ (tiene tool_calls) ─────> action_node ─> summarize_node ─> END
#                                         └─ (no tiene tool_calls) ──> END

builder.add_edge(START, "router_node")
builder.add_conditional_edges("router_node", route_intent, {
    "chat_node": "chat_node",
    "command_node": "command_node"
})
builder.add_edge("chat_node", END)
builder.add_conditional_edges("command_node", should_use_tools, {
    "action_node": "action_node",
    "end": END
})
builder.add_edge("action_node", "summarize_node")
builder.add_edge("summarize_node", END)