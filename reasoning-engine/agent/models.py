from enum import Enum
import operator
from typing import Annotated, Any, Dict, List, Optional, Sequence, TypedDict
from langchain_core.messages import BaseMessage
from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class EventType(str, Enum):
    """Enumeration of event types handled across the system messaging fabric."""
    TOOL_REGISTRY_BROADCAST = "TOOL_REGISTRY_BROADCAST"
    EXECUTION_REQUEST = "EXECUTION_REQUEST"
    EXECUTION_RESPONSE = "EXECUTION_RESPONSE"


class EventMetadata(BaseModel):
    """Metadata attached to every message envelope for routing and tracing."""
    model_config = ConfigDict(populate_by_name=True)

    event_id: str = Field(..., validation_alias=AliasChoices("event_id", "eventId"), serialization_alias="eventId")
    correlation_id: str = Field(..., validation_alias=AliasChoices("correlation_id", "correlationId"), serialization_alias="correlationId")
    timestamp: int
    source: str
    event_type: EventType = Field(..., validation_alias=AliasChoices("event_type", "eventType"), serialization_alias="eventType")


class ToolExecutionRequestPayload(BaseModel):
    """Payload dispatched when the agent requests an external tool execution."""
    model_config = ConfigDict(populate_by_name=True)

    tool_name: str = Field(..., validation_alias=AliasChoices("tool_name", "toolName"), serialization_alias="toolName")
    arguments: Dict[str, Any]


class ToolExecutionResponsePayload(BaseModel):
    """Payload returned by the execution service after running a tool."""
    model_config = ConfigDict(populate_by_name=True)

    tool_name: str = Field(..., validation_alias=AliasChoices("tool_name", "toolName"), serialization_alias="toolName")
    status: str
    output: Optional[str] = None
    error_code: Optional[str] = Field(None, validation_alias=AliasChoices("error_code", "errorCode"), serialization_alias="errorCode")


class ConfirmationRequestPayload(BaseModel):
    """Payload dispatched over WebSocket when the agent requests user authorization for a critical tool."""
    model_config = ConfigDict(populate_by_name=True)

    type: str = "confirmation_request"
    confirmation_id: str = Field(..., validation_alias=AliasChoices("confirmation_id", "confirmationId"), serialization_alias="confirmationId")
    tool_name: str = Field(..., validation_alias=AliasChoices("tool_name", "toolName"), serialization_alias="toolName")
    arguments: Dict[str, Any]
    title: str
    message: str
    severity: str = "CRITICAL"
    target: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class ConfirmationResponsePayload(BaseModel):
    """Payload received from client confirming or denying a critical tool authorization request."""
    model_config = ConfigDict(populate_by_name=True)

    type: str = "confirmation_response"
    confirmation_id: str = Field(..., validation_alias=AliasChoices("confirmation_id", "confirmationId"), serialization_alias="confirmationId")
    confirmed: bool = False


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
