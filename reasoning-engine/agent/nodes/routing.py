"""
Conditional edge routing functions controlling flow across workflow graph nodes.
"""
from typing import Literal
from langchain_core.messages import AIMessage

from ..models import AgentState
from .base import Intent, NodeName


def route_intent(state: AgentState) -> Literal["chat_node", "command_node"]:
    """
    Direct graph workflow execution based on the classified user intent.

    Args:
        state: Current agent state dictionary containing classified intent.

    Returns:
        The target node name ('command_node' or 'chat_node').
    """
    if state.get("intent") == Intent.COMMAND:
        return NodeName.COMMAND.value
    return NodeName.CHAT.value


def should_use_tools(state: AgentState) -> Literal["action_node", "end"]:
    """
    Inspect the model's output message to determine if external tool execution is required.

    Args:
        state: Current agent state containing conversational message history.

    Returns:
        'action_node' if tool calls are present in the latest message; 'end' otherwise.
    """
    messages = state.get("messages", [])
    if not messages:
        return NodeName.END.value

    last_message = messages[-1]
    if isinstance(last_message, AIMessage) and bool(last_message.tool_calls):
        return NodeName.ACTION.value
    return NodeName.END.value


__all__ = [
    "route_intent",
    "should_use_tools",
]
