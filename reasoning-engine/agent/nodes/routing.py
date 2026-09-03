"""
Conditional edge routing functions controlling the flow across graph nodes.
"""
from typing import Literal
from langchain_core.messages import AIMessage
from ..models import AgentState


def route_intent(state: AgentState) -> Literal["chat_node", "command_node"]:
    """
    Directs graph flow based on the classified user intent.

    Args:
        state: Current agent state.

    Returns:
        The target node name ('command_node' or 'chat_node').
    """
    if state.get("intent") == "COMMAND":
        return "command_node"
    return "chat_node"


def should_use_tools(state: AgentState) -> Literal["action_node", "end"]:
    """
    Inspects the AI model's output to determine if external tool execution is required.

    Args:
        state: Current agent state.

    Returns:
        'action_node' if tool calls are present, or 'end' to terminate execution.
    """
    messages = state.get("messages", [])
    if not messages:
        return "end"

    last_message = messages[-1]
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "action_node"
    return "end"
