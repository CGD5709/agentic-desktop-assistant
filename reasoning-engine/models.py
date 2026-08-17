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

# --- Payloads específicos ---

class ToolExecutionRequestPayload(BaseModel):
    tool_name: str = Field(..., alias="toolName")
    arguments: Dict[str, Any]

class ToolExecutionResponsePayload(BaseModel):
    tool_name: str = Field(..., alias="toolName")
    status: str  # ej. "SUCCESS", "ERROR", "PENDING_APPROVAL"
    output: Optional[str] = None
    error_code: Optional[str] = Field(None, alias="errorCode")

# --- Envoltorio principal (Custom Envelope) ---

class EventEnvelope(BaseModel):
    metadata: EventMetadata
    payload: Dict[str, Any]  
    # Nota: El payload es un diccionario genérico en la raíz. 
    # Dependiendo del event_type en metadata, lo parsearemos luego 
    # al modelo específico (Request o Response).