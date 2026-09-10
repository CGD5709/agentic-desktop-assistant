"""
WebSocket API router and message dispatching layer.
"""
import json
import uuid
from typing import Any, Awaitable, Callable, Dict, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph

from agent import AgentRuntime, AgentState
from services.connection_manager import WebSocketConnectionManager

router = APIRouter()

MessageHandler = Callable[[WebSocket, Dict[str, Any]], Awaitable[None]]


async def handle_ping_message(websocket: WebSocket, payload: Dict[str, Any]) -> None:
    """
    Handle client heartbeat ping and return a pong acknowledgment.

    Args:
        websocket: Active client WebSocket session.
        payload: Received message payload dictionary.
    """
    ws_manager: WebSocketConnectionManager = websocket.app.state.ws_manager
    await ws_manager.send_personal({"type": "pong"}, websocket)


async def handle_user_message(websocket: WebSocket, payload: Dict[str, Any]) -> None:
    """
    Process incoming user message by invoking the LangGraph orchestrator graph.

    Transitions client state (THINKING -> IDLE) and streams assistant responses
    or courteous error notifications back through the WebSocket session.

    Args:
        websocket: Active client WebSocket session.
        payload: Interaction payload dictionary containing the user prompt under 'content'.
    """
    ws_manager: WebSocketConnectionManager = websocket.app.state.ws_manager
    app_graph: Optional[CompiledStateGraph] = getattr(websocket.app.state, "app_graph", None)
    config: RunnableConfig = websocket.app.state.config

    raw_content = payload.get("content", "")
    if not isinstance(raw_content, str) or not raw_content.strip():
        return

    user_text = raw_content.strip()

    if app_graph is None:
        # TODO: Replace print with a standardized logging framework (e.g., logging/structlog).
        print("⚠️ [WebSocket] Message received before reasoning engine (app_graph) was initialized.")
        await ws_manager.send_personal({
            "type": "assistant_message",
            "content": "El motor de razonamiento se está inicializando o no está disponible en este momento. Por favor, intente de nuevo en unos segundos.",
        }, websocket)
        return

    # TODO: Replace print with a standardized logging framework (e.g., logging/structlog).
    print(f"📥 [WS User]: {user_text}")

    await ws_manager.send_personal({
        "type": "status",
        "state": "THINKING",
    }, websocket)

    try:
        state: AgentState = {
            "messages": [HumanMessage(content=user_text)],
            "correlation_id": str(uuid.uuid4()),
        }

        result = await app_graph.ainvoke(state, config=config)
        last_msg = result["messages"][-1]
        assistant_text = last_msg.content if isinstance(last_msg.content, str) else ""

        # TODO: Replace print with a standardized logging framework (e.g., logging/structlog).
        print(f"🤖 [WS Jarvis]: {assistant_text[:80]}...")

        await ws_manager.send_personal({
            "type": "assistant_message",
            "content": assistant_text,
        }, websocket)

    except Exception as err:
        # TODO: Replace print with a standardized logging framework (e.g., logging/structlog).
        print(f"❌ [WebSocket] LangGraph execution error: {err}")
        await ws_manager.send_personal({
            "type": "assistant_message",
            "content": f"He experimentado una anomalía en mi núcleo de procesamiento: {err}",
        }, websocket)
    finally:
        await ws_manager.send_personal({
            "type": "status",
            "state": "IDLE",
        }, websocket)


MESSAGE_DISPATCHER: Dict[str, MessageHandler] = {
    "ping": handle_ping_message,
    "user_message": handle_user_message,
}


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """
    Primary WebSocket entry point routing messages via the Dispatcher pattern.

    Manages connection lifecycle, authenticates application readiness, dispatches
    incoming messages to registered handlers, and ensures graceful disconnection.

    Args:
        websocket: Incoming WebSocket connection request.
    """
    ws_manager: Optional[WebSocketConnectionManager] = getattr(
        websocket.app.state, "ws_manager", None
    )
    runtime: Optional[AgentRuntime] = getattr(websocket.app.state, "runtime", None)

    if ws_manager is None:
        await websocket.close(code=1011, reason="Server not initialized.")
        return

    await ws_manager.connect(websocket)

    tools = [t["function"]["name"] for t in runtime.dynamic_tools] if runtime else []
    await ws_manager.send_personal({
        "type": "connected",
        "message": "Sistemas de J.A.R.V.I.S en línea y listos para interactuar.",
        "tools": tools,
    }, websocket)

    try:
        while True:
            raw_data = await websocket.receive_text()
            try:
                msg = json.loads(raw_data)
            except (json.JSONDecodeError, TypeError):
                continue

            if not isinstance(msg, dict):
                continue

            msg_type = msg.get("type", "")
            handler = MESSAGE_DISPATCHER.get(msg_type)
            if handler:
                await handler(websocket, msg)
            else:
                # TODO: Replace print with a standardized logging framework (e.g., logging/structlog).
                print(f"⚠️ [WebSocket] Unrecognized or unhandled message type: '{msg_type}'")

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        # TODO: Replace print with a standardized logging framework (e.g., logging/structlog).
        print(f"⚠️ [WebSocket] Client session error: {e}")
        ws_manager.disconnect(websocket)
