from pydantic import BaseModel, Field
from typing import Any, Dict, Optional
from enum import Enum

class EventType(str, Enum):
    TOOL_REGISTRY_BROADCAST = "TOOL_REGISTRY_BROADCAST"
    EXECUTION_REQUEST = "EXECUTION_REQUEST"
    EXECUTION_RESPONSE = "EXECUTION_RESPONSE"

class EventMetadata(BaseModel):
    event_id: str = Field(..., alias="eventId")
    correlation_id: str = Field(..., alias="correlationId")
    timestamp: int
    source: str
    event_type: EventType = Field(..., alias="eventType")


# Payload for when the agent requests a tool to be executed | event_type == EXECUTION_REQUEST
class ToolExecutionRequestPayload(BaseModel):
    tool_name: str = Field(..., alias="toolName")
    arguments: Dict[str, Any]

# Payload for when a tool execution response is received | event_type == EXECUTION_RESPONSE
class ToolExecutionResponsePayload(BaseModel):
    tool_name: str = Field(..., alias="toolName")
    status: str #HAY QUE DEFINIR MENSAJES DE ESTATUS  
    output: Optional[str] = None
    error_code: Optional[str] = Field(None, alias="errorCode")


# Custom Envelope for the message
class EventEnvelope(BaseModel):
    metadata: EventMetadata
    payload: Dict[str, Any]  
    # The payload is a generic dictionary in the root. 
    # Depending on the event_type in metadata, we will parse it 
    # to the specific model (Request or Response).