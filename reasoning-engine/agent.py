from typing import Annotated, Sequence, Literal, List, Dict, Any, Optional, TypedDict
import operator
import time
import uuid
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage
from langgraph.graph import StateGraph, START, END

from langchain_ollama import ChatOllama
from rabbitmq import RabbitMQClient
from models import EventEnvelope, EventMetadata, EventType, ToolExecutionRequestPayload

mq_client = RabbitMQClient()

# Herramientas dinámicas registradas desde Java (formato OpenAI)
dynamic_tools: List[Dict[str, Any]] = []

# Modelo optimizado para function calling local (Qwen 2.5 7B)
llm = ChatOllama(model="qwen2.5:7b", temperature=0.2)

# === ESTADO DEL GRAFO ===
class AgentState(TypedDict, total=False):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    intent: Optional[str]
    correlation_id: Optional[str]

# === SYSTEM PROMPTS ===
JARVIS_SYSTEM_PROMPT = """Eres Jarvis, un asistente de escritorio inteligente, sofisticado, leal y eficiente.
Tu propósito es ayudar al usuario de forma natural, ingeniosa y clara.
Mantén tus respuestas conversacionales concisas, amables y elegantes."""

ROUTER_PROMPT = """Eres el clasificador de intenciones para el asistente de escritorio Jarvis.
Tu ÚNICA tarea es clasificar el último mensaje del usuario en una de estas dos categorías:

- CHAT: Conversación casual, saludos ("hola"), agradecimientos ("gracias"), despedidas ("adiós"), respuestas emocionales ("nooo, vuelve", "jaja"), preguntas generales de conocimiento, o cualquier mensaje donde NO se ordene explícitamente realizar una acción técnica en el ordenador.
- COMMAND: El usuario pide explícitamente realizar una acción o tarea técnica en el ordenador (por ejemplo: abrir webs, aplicaciones, matar o cerrar procesos, escanear puertos, analizar rendimiento del sistema, etc.).

IMPORTANTE: Responde ÚNICAMENTE con la palabra exacta 'CHAT' o 'COMMAND', sin comillas, sin explicaciones y sin formato adicional."""

# === 1. NODO ROUTER (Clasificador Semántico de Intenciones) ===
async def router_node(state: AgentState):
    """
    Determina si el usuario quiere charlar o si está dando una orden técnica.
    Esto garantiza 0% de falsos positivos en conversaciones informales.
    """
    messages = list(state.get("messages", []))
    
    last_human_text = ""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            if isinstance(msg.content, str):
                last_human_text = msg.content
            elif isinstance(msg.content, list):
                last_human_text = " ".join(c if isinstance(c, str) else "" for c in msg.content)
            break

    if not last_human_text.strip():
        return {"intent": "CHAT"}

    classification_messages = [
        SystemMessage(content=ROUTER_PROMPT),
        HumanMessage(content=f"Mensaje del usuario: {last_human_text}")
    ]
    
    classification = await llm.ainvoke(classification_messages)
    decision = classification.content.strip().upper() if isinstance(classification.content, str) else "CHAT"
    
    intent = "COMMAND" if "COMMAND" in decision else "CHAT"
    return {"intent": intent}

# === 2. NODO CHAT (Conversación pura sin herramientas) ===
async def chat_node(state: AgentState):
    """
    Maneja la conversación general de Jarvis. Al no tener herramientas
    vinculadas, es imposible que alucine llamadas a tools.
    """
    messages = list(state.get("messages", []))
    
    if not messages or not isinstance(messages[0], SystemMessage):
        messages.insert(0, SystemMessage(content=JARVIS_SYSTEM_PROMPT))
    
    response = await llm.ainvoke(messages)
    return {"messages": [response]}

# === 3. NODO COMMAND (Agente con herramientas vinculadas) ===
async def command_node(state: AgentState):
    """
    Maneja comandos técnicos y llamadas a herramientas del sistema.
    """
    messages = list(state.get("messages", []))
    
    command_system_prompt = SystemMessage(
        content=f"{JARVIS_SYSTEM_PROMPT}\n"
                "El usuario te ha solicitado una orden técnica. "
                "Utiliza las herramientas disponibles adecuadas con los parámetros correctos para cumplir su solicitud."
    )
    
    if not messages or not isinstance(messages[0], SystemMessage):
        messages.insert(0, command_system_prompt)
    
    if dynamic_tools:
        llm_with_tools = llm.bind_tools(dynamic_tools)
        response = await llm_with_tools.ainvoke(messages)
    else:
        response = await llm.ainvoke(messages)
        
    return {"messages": [response]}

# === 4. NODO DE ACCIÓN (Ejecución RPC sobre RabbitMQ) ===
async def action_node(state: AgentState):
    """
    Envía la petición de tool call a Java vía RabbitMQ y espera la respuesta
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
                source="python-reasoning-engine",
                eventType=EventType.EXECUTION_REQUEST
            ),
            payload=request_payload.model_dump(by_alias=True)
        )
        
        routing_key = f"tool.request.{tool_name}"
        print(f" 🚀 [RabbitMQ] Petición lanzada para: {tool_name}")
        
        # Esperamos la respuesta de Java sin límite de tiempo (espera humana posible)
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
    
    summary_instruction = SystemMessage(
        content="Eres Jarvis. Acabas de ejecutar la acción solicitada por el usuario en el ordenador y ya tienes el resultado. "
                "Responde al usuario confirmando de forma BREVE, NATURAL y ELEGANTE qué se ha hecho. "
                "No repitas códigos de error ni términos técnicos a menos que sean necesarios."
    )
    messages.insert(0, summary_instruction)
    
    response = await llm.ainvoke(messages)
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

# Flujo:
# START -> router_node
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