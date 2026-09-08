"""
RabbitMQ listener service and tool discovery payload converter.
"""
import json
from typing import Any, Awaitable, Callable, Dict, List

from agent import AgentRuntime
from services.connection_manager import WebSocketConnectionManager


def convert_execution_tools_to_openai_format(raw_tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convierte el manifiesto de herramientas de execution-service al formato OpenAI."""
    converted = []
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
    Fábrica que construye el callback asíncrono para el consumidor de RabbitMQ.
    Encapsula el acceso a runtime y ws_manager mediante un closure limpio,
    eliminando cualquier dependencia de estado global.
    """

    async def handle_rabbitmq_message(raw_body: str, routing_key: str) -> None:
        if routing_key == "system.discovery.execution_service":
            try:
                data = json.loads(raw_body)
                tools_list = data.get("payload", {}).get("tools", [])
                runtime.dynamic_tools.clear()
                converted_tools = convert_execution_tools_to_openai_format(tools_list)
                runtime.dynamic_tools.extend(converted_tools)
                nombres = [t["function"]["name"] for t in converted_tools]
                print(f"\n📡 [System Discovery] Herramientas recibidas de execution-service: {nombres}")
                # Notificamos a los clientes WebSocket conectados sobre las nuevas herramientas
                await ws_manager.broadcast({
                    "type": "tools_updated",
                    "tools": [t["function"]["name"] for t in runtime.dynamic_tools],
                })
            except Exception as e:
                print(f"\n❌ Error procesando el manifiesto de herramientas: {e}")

    return handle_rabbitmq_message
