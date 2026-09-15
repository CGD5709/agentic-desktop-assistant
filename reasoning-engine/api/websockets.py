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
from logger import clear_log_context, get_logger, set_log_context
from services.connection_manager import WebSocketConnectionManager

logger = get_logger("reasoning_engine.websockets")
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
    correlation_id = str(uuid.uuid4())
    set_log_context(correlation_id=correlation_id)

    if app_graph is None:
        logger.warning("Message received before reasoning engine (app_graph) was initialized.")
        await ws_manager.send_or_broadcast({
            "type": "assistant_message",
            "content": "El motor de razonamiento se está inicializando o no está disponible en este momento. Por favor, intente de nuevo en unos segundos.",
        }, websocket)
        return

    logger.info("Received user prompt: %s", user_text)

    await ws_manager.send_or_broadcast({
        "type": "status",
        "state": "THINKING",
    }, websocket)

    try:
        state: AgentState = {
            "messages": [HumanMessage(content=user_text)],
            "correlation_id": correlation_id,
        }

        result = await app_graph.ainvoke(state, config=config)
        last_msg = result["messages"][-1]
        assistant_text = last_msg.content if isinstance(last_msg.content, str) else ""

        preview = (assistant_text[:80] + "...") if len(assistant_text) > 80 else assistant_text
        logger.info("Generated assistant response: %s", preview)

        await ws_manager.send_or_broadcast({
            "type": "assistant_message",
            "content": assistant_text,
        }, websocket)

    except Exception as err:
        logger.error("LangGraph execution error: %s", err, exc_info=True)
        try:
            await ws_manager.send_or_broadcast({
                "type": "assistant_message",
                "content": f"He experimentado una anomalía en mi núcleo de procesamiento: {err}",
            }, websocket)
        except Exception:
            pass
    finally:
        clear_log_context()
        try:
            await ws_manager.send_or_broadcast({
                "type": "status",
                "state": "IDLE",
            }, websocket)
        except Exception:
            pass


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
            if msg_type == "ping":
                await handle_ping_message(websocket, msg)
            elif msg_type == "user_message":
                await handle_user_message(websocket, msg)
            else:
                logger.warning("Unrecognized or unhandled message type: '%s'", msg_type)

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.warning("Client session error: %s", e)
        ws_manager.disconnect(websocket)
