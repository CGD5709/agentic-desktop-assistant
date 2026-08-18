from typing import Annotated, Sequence, TypedDict, Literal
import operator
import sqlite3
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver

# --- NUEVAS IMPORTACIONES PARA OLLAMA ---
from langchain_ollama import ChatOllama
from langchain_core.tools import tool

# --- 1. Definición de Herramientas y LLM ---

@tool
def execute_git_commit(commit_message: str):
    """Usa esta herramienta para hacer un commit en Git con los cambios actuales del repositorio."""
    # Aquí instanciaremos nuestro EventEnvelope y lo enviaremos por RabbitMQ a Java en el futuro.
    pass

# Inicializamos el motor de Ollama local (Llama 3.1)
# temperature=0 lo hace más analítico y preciso al elegir herramientas
llm = ChatOllama(model="llama3.1", temperature=0)

# Unimos el modelo con las herramientas (así el LLM sabe qué opciones tiene)
llm_with_tools = llm.bind_tools([execute_git_commit])


# --- 2. Definición del Estado ---
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    correlation_id: str 


# --- 3. Nodos y Enrutadores ---
def reasoning_node(state: AgentState):
    """El cerebro real. Le pasamos el historial al LLM y él decide."""
    print(" [Reasoning Node] Llama 3.1 está analizando la conversación...")
    
    # ¡Adiós a los if/else! El LLM lee el historial y genera la respuesta solo.
    response = llm_with_tools.invoke(state["messages"])
    
    return {"messages": [response]}


def action_node(state: AgentState):
    """El ejecutor. Atrapa la petición del LLM y simula la respuesta."""
    print(" [Action Node] Procesando petición de herramienta...")
    last_message = state["messages"][-1]
    
    # Le garantizamos a Pylance que este mensaje es de la IA
    assert isinstance(last_message, AIMessage)
    
    # LangChain guarda las peticiones de herramientas en esta lista
    tool_call = last_message.tool_calls[0] 
    
    print(f"   -> Herramienta solicitada: {tool_call['name']}")
    print(f"   -> Argumentos generados: {tool_call['args']}")
    
    # Simulamos que Java ha hecho el commit y nos devuelve éxito
    commit_msg = tool_call['args'].get('commit_message', 'actualización')
    result_content = f"Éxito: Commit realizado con el mensaje '{commit_msg}'"
    
    # Es OBLIGATORIO devolver un ToolMessage con el ID exacto que generó el LLM
    tool_message = ToolMessage(
        content=result_content,
        tool_call_id=tool_call["id"]
    )
    return {"messages": [tool_message]}


def should_continue(state: AgentState) -> Literal["action", "end"]:
    """El enrutador: Lee la decisión de Llama 3.1 y elige la siguiente flecha."""
    last_message = state["messages"][-1]
    
    # Verificamos explícitamente que es un mensaje de IA antes de buscar tool_calls
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "action"
    
    return "end"


# --- 4. Construcción del Grafo ---
builder = StateGraph(AgentState)

builder.add_node("reasoning", reasoning_node)
builder.add_node("action", action_node)

builder.add_edge(START, "reasoning")

builder.add_conditional_edges(
    "reasoning", 
    should_continue, 
    {
        "action": "action",
        "end": END
    }
)

builder.add_edge("action", "reasoning")

# Conectamos la base de datos SQLite local
db_connection = sqlite3.connect("agent_memory.db", check_same_thread=False)
memory_saver = SqliteSaver(db_connection)

# Compilamos inyectando el checkpointer
agent_graph = builder.compile(checkpointer=memory_saver)