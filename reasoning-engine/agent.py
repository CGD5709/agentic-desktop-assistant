from typing import Annotated, Sequence, TypedDict, Literal
import operator
import time
import uuid
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, START, END

from langchain_ollama import ChatOllama
from rabbitmq import RabbitMQClient
from models import EventEnvelope, EventMetadata, EventType, ToolExecutionRequestPayload

# Instancia global del cliente
mq_client = RabbitMQClient()

# ¡ADIÓS AL HARDCODE! Ya no hay @tool. 
# Aquí guardaremos los esquemas JSON que nos mande Java.
dynamic_tools = []

llm = ChatOllama(model="llama3.1", temperature=0)

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    correlation_id: str 

async def reasoning_node(state: AgentState):
    # En cada turno, vinculamos las herramientas descubiertas dinámicamente
    if dynamic_tools:
        llm_with_tools = llm.bind_tools(dynamic_tools)
        response = await llm_with_tools.ainvoke(state["messages"])
    else:
        # Si Java aún no ha arrancado o no hay herramientas, funciona como un chat normal
        response = await llm.ainvoke(state["messages"])
        
    return {"messages": [response]}

async def action_node(state: AgentState):
    last_message = state["messages"][-1]
    assert isinstance(last_message, AIMessage)
    
    tool_call = last_message.tool_calls[0] 
    tool_name = tool_call['name']
    tool_args = tool_call['args']
    
    tool_call_id = tool_call.get("id")
    assert isinstance(tool_call_id, str), "El ID del tool_call no puede ser nulo"
    
    request_payload = ToolExecutionRequestPayload(
        toolName=tool_name,
        arguments=tool_args
    )
    
    envelope = EventEnvelope(
        metadata=EventMetadata(
            eventId=str(uuid.uuid4()),
            correlationId=tool_call_id, 
            timestamp=int(time.time() * 1000),
            source="python-reasoning-engine",
            eventType=EventType.EXECUTION_REQUEST
        ),
        payload=request_payload.model_dump(by_alias=True)
    )
    
    routing_key = f"tool.request.{tool_name}"
    await mq_client.publish(routing_key, envelope)
    
    return {}

def should_continue(state: AgentState) -> Literal["action", "end"]:
    last_message = state["messages"][-1]
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "action"
    return "end"

builder = StateGraph(AgentState)
builder.add_node("reasoning", reasoning_node)
builder.add_node("action", action_node)

builder.add_edge(START, "reasoning")
builder.add_conditional_edges("reasoning", should_continue, {"action": "action", "end": END})
builder.add_edge("action", END)