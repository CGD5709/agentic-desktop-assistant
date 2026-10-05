"""
WebSocket API router and message dispatching layer.
"""

import asyncio
import json
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from agent import AgentRuntime, AgentState
from agent.email_models import EmailCategory, RawEmailDTO
from agent.models import ConfirmationResponsePayload
from agent.voice_cleaner import clean_text_for_speech
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph
from logger import clear_log_context, get_logger, set_log_context
from services.connection_manager import WebSocketConnectionManager
from services.task_scheduler.models import TaskCreateRequest, TriggerConfig, TriggerType

logger = get_logger("reasoning_engine.websockets")
router = APIRouter()

MessageHandler = Callable[[WebSocket, dict[str, Any]], Awaitable[None]]

# Track running inference tasks per WebSocket connection for cancellation
_active_tasks: dict[WebSocket, asyncio.Task[None]] = {}


async def handle_ping_message(websocket: WebSocket, payload: dict[str, Any]) -> None:
    """
    Handle client heartbeat ping and return a pong acknowledgment.

    Args:
        websocket: Active client WebSocket session.
        payload: Received message payload dictionary.
    """
    ws_manager: WebSocketConnectionManager = websocket.app.state.ws_manager
    await ws_manager.send_personal({"type": "pong"}, websocket)


async def handle_confirmation_response(
    websocket: WebSocket, payload: dict[str, Any]
) -> None:
    """
    Process client response to a Human-in-the-Loop confirmation request.

    Args:
        websocket: Active client WebSocket session.
        payload: Payload containing 'confirmation_id' and boolean 'confirmed'.
    """
    runtime: AgentRuntime | None = getattr(websocket.app.state, "runtime", None)
    if runtime is None or runtime.confirmation_manager is None:
        logger.warning(
            "Confirmation response received but ConfirmationManager is not initialized."
        )
        return

    try:
        response_model = ConfirmationResponsePayload.model_validate(payload)
        runtime.confirmation_manager.resolve_confirmation(
            response_model.confirmation_id, response_model.confirmed
        )
    except Exception as e:
        logger.warning("Invalid confirmation response payload: %s (%s)", payload, e)


async def handle_stop_message(websocket: WebSocket, payload: dict[str, Any]) -> None:
    """
    Cancel active reasoning execution and pending confirmations upon receiving explicit stop command from user.

    Args:
        websocket: Active client WebSocket session.
        payload: Received stop payload.
    """
    ws_manager: WebSocketConnectionManager = websocket.app.state.ws_manager
    runtime: AgentRuntime | None = getattr(websocket.app.state, "runtime", None)
    if runtime and runtime.confirmation_manager:
        runtime.confirmation_manager.cancel_all()

    task = _active_tasks.get(websocket)
    if task and not task.done():
        logger.info("Cancelling active LangGraph task upon user request.")
        task.cancel()

    await ws_manager.send_or_broadcast(
        {
            "type": "status",
            "state": "IDLE",
        },
        websocket,
    )


async def handle_email_action(websocket: WebSocket, payload: dict[str, Any]) -> None:
    """
    Handle email draft actions triggered directly from the React frontend central deck.
    Supports generating drafts, approving/sending, discarding, or regenerating drafts.
    """
    ws_manager: WebSocketConnectionManager = websocket.app.state.ws_manager
    runtime: AgentRuntime | None = getattr(websocket.app.state, "runtime", None)
    action = payload.get("action", "")
    draft_id = payload.get("draftId") or payload.get("draft_id")

    if action == "discard_draft":
        logger.info("User discarded email draft: %s", draft_id)
        if runtime and runtime.email_service and draft_id:
            runtime.email_service.remove_draft(draft_id)
        await ws_manager.send_or_broadcast(
            {"type": "email_draft_cleared", "draftId": draft_id}, websocket
        )

    elif action in ("generate_draft", "regenerate_draft"):
        email_data = payload.get("email", {})
        if not email_data and (payload.get("email_id") or payload.get("id")):
            email_data = payload

        email_id = str(
            email_data.get("id")
            or email_data.get("email_id")
            or payload.get("email_id")
            or f"msg-{uuid.uuid4().hex[:6]}"
        )
        logger.info("Generating reply draft for email %s (action=%s)", email_id, action)

        try:
            raw_email = RawEmailDTO(
                id=email_id,
                account=str(email_data.get("account", "GMAIL")),
                accountAddress=str(
                    email_data.get("account_address")
                    or email_data.get("accountAddress", "")
                ),
                subject=str(email_data.get("subject", "(Sin asunto)")),
                fromName=str(
                    email_data.get("from_name") or email_data.get("fromName", "")
                ),
                fromAddress=str(
                    email_data.get("from_address") or email_data.get("fromAddress", "")
                ),
                replyToAddress=str(
                    email_data.get("reply_to_address")
                    or email_data.get("replyToAddress", "")
                ),
                bodyText=str(
                    email_data.get("body_text") or email_data.get("bodyText", "")
                ),
                bodySnippet=str(
                    email_data.get("body_snippet") or email_data.get("bodySnippet", "")
                ),
            )

            cat_str = str(email_data.get("category", "NOT IMPORTANT")).upper()
            try:
                cat = EmailCategory(cat_str)
            except Exception:
                cat = EmailCategory.NOT_IMPORTANT

            urgency = int(email_data.get("urgency_score", 1))
            instructions = payload.get("instructions")

            if runtime and runtime.email_service:
                draft = await runtime.email_service.create_draft(
                    email=raw_email,
                    category=cat,
                    urgency_score=urgency,
                    user_instructions=instructions,
                )
                await ws_manager.send_or_broadcast(
                    draft.model_dump(by_alias=True), websocket
                )
            else:
                logger.warning(
                    "EmailAssistantService not available on runtime for generating draft."
                )
        except Exception as e:
            logger.exception(
                "Error generating draft for email %s: %s", email_id, e, exc_info=True
            )

    elif action == "approve_and_send":
        logger.info("User approved sending draft %s from frontend deck", draft_id)
        account = payload.get("account", "GMAIL")
        recipient = payload.get("recipient", "")
        subject = payload.get("subject", "")
        body = payload.get("body", "")

        if runtime and runtime.email_service and draft_id:
            runtime.email_service.remove_draft(draft_id)

        prompt = (
            f"Envía el correo electrónico aprobado desde la cuenta {account} hacia '{recipient}' "
            f"con el asunto '{subject}' y el siguiente cuerpo:\n\n{body}"
        )
        correlation_id = str(uuid.uuid4())
        app_graph: CompiledStateGraph | None = getattr(
            websocket.app.state, "app_graph", None
        )
        default_config: RunnableConfig = {
            "configurable": {"thread_id": "sesion-produccion"}
        }
        config: RunnableConfig = getattr(websocket.app.state, "config", default_config)

        if app_graph is None:
            logger.warning(
                "Email action received before reasoning engine (app_graph) was initialized."
            )
            await ws_manager.send_or_broadcast(
                {
                    "type": "assistant_message",
                    "content": "El motor de razonamiento se está inicializando o no está disponible en este momento. Por favor, intente de nuevo en unos segundos.",
                    "speech_text": "El motor de razonamiento no está disponible en este momento.",
                },
                websocket,
            )
            return

        # Cancel previous task if still running
        prev_task = _active_tasks.get(websocket)
        if prev_task and not prev_task.done():
            prev_task.cancel()

        task = asyncio.create_task(
            _execute_user_prompt(
                websocket=websocket,
                user_text=prompt,
                correlation_id=correlation_id,
                app_graph=app_graph,
                config=config,
                ws_manager=ws_manager,
            )
        )
        _active_tasks[websocket] = task


async def handle_clear_history(websocket: WebSocket, payload: dict[str, Any]) -> None:
    """
    Clear active thread checkpoints and dialogue history upon client request.
    """
    from pathlib import Path

    import aiosqlite

    ws_manager: WebSocketConnectionManager = websocket.app.state.ws_manager
    default_config: RunnableConfig = {
        "configurable": {"thread_id": "sesion-produccion"}
    }
    config: RunnableConfig = getattr(websocket.app.state, "config", default_config)
    thread_id = config.get("configurable", {}).get("thread_id", "sesion-produccion")

    logger.info(
        "Clearing conversational checkpoint history for thread '%s'...", thread_id
    )
    try:
        db_path = Path(__file__).resolve().parent.parent / "data" / "agent_memory.db"
        if db_path.exists():
            async with aiosqlite.connect(str(db_path)) as db:
                await db.execute(
                    "DELETE FROM checkpoints WHERE thread_id = ?", (thread_id,)
                )
                await db.execute("DELETE FROM writes WHERE thread_id = ?", (thread_id,))
                await db.commit()
            logger.info(
                "Database checkpoint records cleared for thread '%s'", thread_id
            )
    except Exception as e:
        logger.warning("Error clearing SQLite checkpointer records: %s", e)

    await ws_manager.send_personal(
        {
            "type": "history_cleared",
            "message": "Historial de conversación reiniciado con éxito.",
        },
        websocket,
    )


async def handle_tasks_message(websocket: WebSocket, payload: dict[str, Any]) -> None:
    """
    Handle task scheduler actions (get list, create task, toggle status, delete, or run now).
    """
    ws_manager: WebSocketConnectionManager = websocket.app.state.ws_manager
    runtime: AgentRuntime | None = getattr(websocket.app.state, "runtime", None)
    if not runtime or not runtime.task_scheduler:
        logger.warning("TaskSchedulerService not available in runtime.")
        return

    msg_type = payload.get("type", "")

    if msg_type in ("tasks_get", "get_tasks"):
        tasks = await runtime.task_scheduler.list_tasks()
        await ws_manager.send_personal(
            {
                "type": "tasks_list",
                "tasks": [t.model_dump() for t in tasks],
            },
            websocket,
        )

    elif msg_type == "task_create":
        task_data = payload.get("task", {})
        try:
            req = TaskCreateRequest(
                name=str(task_data.get("name") or "Nueva Tarea"),
                description=str(task_data.get("description") or ""),
                tool_name=str(task_data.get("tool_name") or "notificacion_proactiva"),
                tool_arguments=task_data.get("tool_arguments") or {},
                trigger_type=TriggerType(task_data.get("trigger_type", "ONE_SHOT")),
                trigger_config=TriggerConfig.model_validate(
                    task_data.get("trigger_config") or {}
                ),
                notify_voice=bool(task_data.get("notify_voice", True)),
            )
            created = await runtime.task_scheduler.create_task(req)
            logger.info("Task created via WebSocket: %s (%s)", created.name, created.id)
        except Exception as e:
            logger.error("Failed to create task via WebSocket: %s", e)

    elif msg_type == "task_toggle":
        task_id = str(payload.get("task_id") or "")
        enabled = bool(payload.get("enabled", True))
        if task_id:
            await runtime.task_scheduler.toggle_task(task_id, enabled)

    elif msg_type == "task_delete":
        task_id = str(payload.get("task_id") or "")
        if task_id:
            await runtime.task_scheduler.delete_task(task_id)

    elif msg_type == "task_run_now":
        task_id = str(payload.get("task_id") or "")
        if task_id:
            asyncio.create_task(
                runtime.task_scheduler.execute_task(task_id, is_manual=True)
            )


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
        await ws_manager.send_or_broadcast(
            {
                "type": "status",
                "state": "THINKING",
            },
            websocket,
        )

        state: AgentState = {
            "messages": [HumanMessage(content=user_text)],
            "correlation_id": correlation_id,
        }

        result = await app_graph.ainvoke(state, config=config)
        last_msg = result["messages"][-1]
        assistant_text = last_msg.content if isinstance(last_msg.content, str) else ""

        preview = (
            (assistant_text[:80] + "...")
            if len(assistant_text) > 80
            else assistant_text
        )
        logger.info("Generated assistant response: %s", preview)

        # Generate cleaned speech text for TTS audio synthesis
        speech_text = clean_text_for_speech(assistant_text)

        await ws_manager.send_or_broadcast(
            {
                "type": "assistant_message",
                "content": assistant_text,
                "speech_text": speech_text,
            },
            websocket,
        )

    except asyncio.CancelledError:
        logger.info("LangGraph execution cancelled by client.")
        await ws_manager.send_or_broadcast(
            {
                "type": "assistant_message",
                "content": "Operación cancelada por el usuario.",
                "speech_text": "Operación cancelada.",
            },
            websocket,
        )
    except Exception as err:
        logger.exception("LangGraph execution error: %s", err)
        try:
            error_msg = (
                f"He experimentado una anomalía en mi núcleo de procesamiento: {err}"
            )
            await ws_manager.send_or_broadcast(
                {
                    "type": "assistant_message",
                    "content": error_msg,
                    "speech_text": "He experimentado una anomalía al procesar su solicitud.",
                },
                websocket,
            )
        except Exception:
            pass
    finally:
        clear_log_context()
        try:
            await ws_manager.send_or_broadcast(
                {
                    "type": "status",
                    "state": "IDLE",
                },
                websocket,
            )
        except Exception:
            pass


async def handle_user_message(websocket: WebSocket, payload: dict[str, Any]) -> None:
    """
    Process incoming user message by scheduling the LangGraph orchestrator task.

    Args:
        websocket: Active client WebSocket session.
        payload: Interaction payload dictionary containing the user prompt under 'content'.
    """
    ws_manager: WebSocketConnectionManager = websocket.app.state.ws_manager
    app_graph: CompiledStateGraph | None = getattr(
        websocket.app.state, "app_graph", None
    )
    default_config: RunnableConfig = {
        "configurable": {"thread_id": "sesion-produccion"}
    }
    config: RunnableConfig = getattr(websocket.app.state, "config", default_config)

    raw_content = payload.get("content", "")
    if not isinstance(raw_content, str) or not raw_content.strip():
        return

    user_text = raw_content.strip()
    correlation_id = str(uuid.uuid4())

    if app_graph is None:
        logger.warning(
            "Message received before reasoning engine (app_graph) was initialized."
        )
        await ws_manager.send_or_broadcast(
            {
                "type": "assistant_message",
                "content": "El motor de razonamiento se está inicializando o no está disponible en este momento. Por favor, intente de nuevo en unos segundos.",
                "speech_text": "El motor de razonamiento no está disponible en este momento.",
            },
            websocket,
        )
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
    ws_manager: WebSocketConnectionManager | None = getattr(
        websocket.app.state, "ws_manager", None
    )
    runtime: AgentRuntime | None = getattr(websocket.app.state, "runtime", None)

    if ws_manager is None:
        await websocket.close(code=1011, reason="Server not initialized.")
        return

    await ws_manager.connect(websocket)

    tools = [t["function"]["name"] for t in runtime.dynamic_tools] if runtime else []
    await ws_manager.send_personal(
        {
            "type": "connected",
            "message": "Sistemas de J.A.R.V.I.S en línea y listos para interactuar.",
            "tools": tools,
        },
        websocket,
    )

    if runtime and runtime.task_scheduler:
        try:
            initial_tasks = await runtime.task_scheduler.list_tasks()
            await ws_manager.send_personal(
                {
                    "type": "tasks_list",
                    "tasks": [t.model_dump() for t in initial_tasks],
                },
                websocket,
            )
        except Exception as e:
            logger.warning("Error fetching initial tasks on WS connection: %s", e)

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
            elif msg_type == "confirmation_response":
                await handle_confirmation_response(websocket, msg)
            elif msg_type in ("stop", "cancel"):
                await handle_stop_message(websocket, msg)
            elif msg_type in ("clear_history", "clear_messages"):
                await handle_clear_history(websocket, msg)
            elif msg_type == "email_action":
                await handle_email_action(websocket, msg)
            elif msg_type in (
                "tasks_get",
                "get_tasks",
                "task_create",
                "task_toggle",
                "task_delete",
                "task_run_now",
            ):
                await handle_tasks_message(websocket, msg)
            else:
                logger.warning("Unrecognized or unhandled message type: '%s'", msg_type)

    except WebSocketDisconnect:
        if runtime and runtime.confirmation_manager:
            runtime.confirmation_manager.cancel_all()
        task = _active_tasks.pop(websocket, None)
        if task and not task.done():
            task.cancel()
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.warning("Client session error: %s", e)
        if runtime and runtime.confirmation_manager:
            runtime.confirmation_manager.cancel_all()
        task = _active_tasks.pop(websocket, None)
        if task and not task.done():
            task.cancel()
        ws_manager.disconnect(websocket)
