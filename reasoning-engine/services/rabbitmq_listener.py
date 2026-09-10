"""
RabbitMQ listener service and tool discovery payload converter.
"""
import json
from typing import Any, Awaitable, Callable, Dict, List

from agent import AgentRuntime
from services.connection_manager import WebSocketConnectionManager


def convert_execution_tools_to_openai_format(
    raw_tools: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Transform raw tool definitions from execution-service into the OpenAI function schema.

    Args:
        raw_tools: List of tool specification dictionaries received via RabbitMQ discovery.

    Returns:
        List of OpenAI-compliant function tool definitions ready for LLM binding.
    """
    converted: List[Dict[str, Any]] = []
    for tool in raw_tools:
        openai_tool = {
            "type": "function",
            "function": {
                "name": tool.get("name", ""),
                "description": tool.get("description", ""),
                "parameters": tool.get("parameters", {"type": "object", "properties": {}}),
            },
        }
        converted.append(openai_tool)
    return converted


def create_rabbitmq_message_handler(
    runtime: AgentRuntime,
    ws_manager: WebSocketConnectionManager,
) -> Callable[[str, str], Awaitable[None]]:
    """
    Factory creating an asynchronous callback handler for RabbitMQ message consumption.

    Encapsulates references to AgentRuntime and WebSocketConnectionManager via closure,
    adhering to Dependency Injection principles and avoiding module-level mutable state.

    Args:
        runtime: The central agent runtime instance holding dynamic tools.
        ws_manager: Connection manager used to broadcast tool updates to connected clients.

    Returns:
        An asynchronous callback expecting the raw message payload and routing key.
    """

    async def handle_rabbitmq_message(raw_body: str, routing_key: str) -> None:
        if routing_key == "system.discovery.execution_service":
            try:
                data = json.loads(raw_body)
                tools_list = data.get("payload", {}).get("tools", [])
                converted_tools = convert_execution_tools_to_openai_format(tools_list)

                runtime.dynamic_tools.clear()
                runtime.dynamic_tools.extend(converted_tools)

                tool_names = [t["function"]["name"] for t in converted_tools]
                # TODO: Replace print with a standardized logging framework (e.g., logging/structlog).
                print(f"\n📡 [System Discovery] Tools registered from execution-service: {tool_names}")

                await ws_manager.broadcast({
                    "type": "tools_updated",
                    "tools": [t["function"]["name"] for t in runtime.dynamic_tools],
                })
            except Exception as e:
                # TODO: Replace print with a standardized logging framework (e.g., logging/structlog).
                print(f"\n❌ [System Discovery] Error processing tool discovery payload: {e}")

    return handle_rabbitmq_message
