"""
Backward-compatibility shim for models.
Exposes models from the agent.models package to ensure non-breaking imports.
"""
from agent.models import (
    EventType,
    EventMetadata,
    ToolExecutionRequestPayload,
    ToolExecutionResponsePayload,
    EventEnvelope,
    AgentState,
)

__all__ = [
    "EventType",
    "EventMetadata",
    "ToolExecutionRequestPayload",
    "ToolExecutionResponsePayload",
    "EventEnvelope",
    "AgentState",
]