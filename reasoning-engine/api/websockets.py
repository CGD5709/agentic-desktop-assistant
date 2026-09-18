"""
WebSocket API router and message dispatching layer.
"""
import asyncio
import json
import uuid
from typing import Any, Awaitable, Callable, Dict, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph

from agent import AgentRuntime, AgentState
from agent.voice_cleaner import clean_text_for_speech
from logger import clear_log_context, get_logger, set_log_context
from services.connection_manager import WebSocketConnectionManager

logger = get_logger("reasoning_engine.websockets")
router = APIRouter()

MessageHandler = Callable[[WebSocket, Dict[str, Any]], Awaitable[None]]

# Track running inference tasks per WebSocket connection for cancellation
_active_tasks: Dict[WebSocket, asyncio.Task[None]] = {}


async def handle_ping_message(websocket: WebSocket, payload: Dict[str, Any]) -> None:
    """
    Handle client heartbeat ping and return a pong acknowledgment.

    Args:
        websocket: Active client WebSocket session.
        payload: Received message payload dictionary.
    """
    ws_manager: WebSocketConnectionManager = websocket.app.state.ws_manager
    await ws_manager.send_personal({"type": "pong"}, websocket)


async def handle_stop_message(websocket: WebSocket, payload: Dict[str, Any]) -> None:
    """
    Cancel active reasoning execution upon receiving explicit stop command from user.

    Args:
        websocket: Active client WebSocket session.
        payload: Received stop payload.
    """
    ws_manager: WebSocketConnectionManager = websocket.app.state.ws_manager
    task = _active_tasks.get(websocket)
    if task and not task.done():
        logger.info("Cancelling active LangGraph task upon user request.")
        task.cancel()

    await ws_manager.send_or_broadcast({
        "type": "status",
        "state": "IDLE",
    }, websocket)


async def _execute_user_prompt(
    websocket: WebSocket,
    user_text: str,
    correlation_id: str,
    app_graph: CompiledStateGraph,
    config: RunnableConfig,
    ws_manager: WebSocketConnectionManager,
) -> None:
    """Internal task runner for orchestrator invocation."""
    set_log_context(correlation_id=correlation_id)
    try:
        await ws_manager.send_or_broadcast({
            "type": "status",
            "state": "THINKING",
        }, websocket)

        state: AgentState = {
            "messages": [HumanMessage(content=user_text)],
            "correlation_id": correlation_id,
        }

        result = await app_graph.ainvoke(state, config=config)
        last_msg = result["messages"][-1]
        assistant_text = last_msg.content if isinstance(last_msg.content, str) else ""

        preview = (assistant_text[:80] + "...") if len(assistant_text) > 80 else assistant_text
        logger.info("Generated assistant response: %s", preview)

        # Generate cleaned speech text for TTS audio synthesis
        speech_text = clean_text_for_speech(assistant_text)

        await ws_manager.send_or_broadcast({
            "type": "assistant_message",
            "content": assistant_text,
            "speech_text": speech_text,
        }, websocket)

    except asyncio.CancelledError:
        logger.info("LangGraph execution cancelled by client.")
        await ws_manager.send_or_broadcast({
            "type": "assistant_message",
            "content": "Operación cancelada por el usuario.",
            "speech_text": "Operación cancelada.",
        }, websocket)
    except Exception as err:
        logger.error("LangGraph execution error: %s", err, exc_info=True)
        try:
            error_msg = f"He experimentado una anomalía en mi núcleo de procesamiento: {err}"
            await ws_manager.send_or_broadcast({
                "type": "assistant_message",
                "content": error_msg,
                "speech_text": "He experimentado una anomalía al procesar su solicitud.",
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


async def handle_user_message(websocket: WebSocket, payload: Dict[str, Any]) -> None:
    """
    Process incoming user message by scheduling the LangGraph orchestrator task.

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

    if app_graph is None:
        logger.warning("Message received before reasoning engine (app_graph) was initialized.")
        await ws_manager.send_or_broadcast({
            "type": "assistant_message",
            "content": "El motor de razonamiento se está inicializando o no está disponible en este momento. Por favor, intente de nuevo en unos segundos.",
            "speech_text": "El motor de razonamiento no está disponible en este momento.",
        }, websocket)
        return

    logger.info("Received user prompt: %s", user_text)

    # Cancel previous task if still running
    prev_task = _active_tasks.get(websocket)
    if prev_task and not prev_task.done():
        prev_task.cancel()

    task = asyncio.create_task(
        _execute_user_prompt(
            websocket=websocket,
            user_text=user_text,
            correlation_id=correlation_id,
            app_graph=app_graph,
            config=config,
            ws_manager=ws_manager,
        )
    )
    _active_tasks[websocket] = task


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
            elif msg_type in ("stop", "cancel"):
                await handle_stop_message(websocket, msg)
            else:
                logger.warning("Unrecognized or unhandled message type: '%s'", msg_type)

    except WebSocketDisconnect:
        task = _active_tasks.pop(websocket, None)
        if task and not task.done():
            task.cancel()
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.warning("Client session error: %s", e)
        task = _active_tasks.pop(websocket, None)
        if task and not task.done():
            task.cancel()
        ws_manager.disconnect(websocket)
