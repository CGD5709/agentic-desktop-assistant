from enum import Enum
import operator
from typing import Annotated, Any, Dict, List, Optional, Sequence, TypedDict
from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Enumeration of event types handled across the system messaging fabric."""
    TOOL_REGISTRY_BROADCAST = "TOOL_REGISTRY_BROADCAST"
    EXECUTION_REQUEST = "EXECUTION_REQUEST"
    EXECUTION_RESPONSE = "EXECUTION_RESPONSE"


class EventMetadata(BaseModel):
    """Metadata attached to every message envelope for routing and tracing."""
    event_id: str = Field(..., alias="eventId")
    correlation_id: str = Field(..., alias="correlationId")
    timestamp: int
    source: str
    event_type: EventType = Field(..., alias="eventType")


class ToolExecutionRequestPayload(BaseModel):
    """Payload dispatched when the agent requests an external tool execution."""
    tool_name: str = Field(..., alias="toolName")
    arguments: Dict[str, Any]


class ToolExecutionResponsePayload(BaseModel):
    """Payload returned by the execution service after running a tool."""
    tool_name: str = Field(..., alias="toolName")
    status: str
    output: Optional[str] = None
    error_code: Optional[str] = Field(None, alias="errorCode")


class EventEnvelope(BaseModel):
    """Standard message envelope for inter-process communication."""
    metadata: EventMetadata
    payload: Dict[str, Any]


class AgentState(TypedDict, total=False):
    """State schema for the LangGraph orchestrator graph."""

    # operator.add acts as a state reducer: it instructs LangGraph to append 
    # new messages to the existing sequence rather than overwriting the list.
    messages: Annotated[Sequence[BaseMessage], operator.add]
    intent: Optional[str]
    correlation_id: Optional[str]
    retrieved_memories: Optional[List[Dict[str, Any]]]
