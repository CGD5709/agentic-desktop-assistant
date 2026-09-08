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
    """Maneja el latido ping/pong para mantener viva la conexión."""
    ws_manager: WebSocketConnectionManager = websocket.app.state.ws_manager
    await ws_manager.send_personal({"type": "pong"}, websocket)


async def handle_user_message(websocket: WebSocket, payload: Dict[str, Any]) -> None:
    """Procesa mensajes de usuario ejecutando el flujo de razonamiento en LangGraph."""
    ws_manager: WebSocketConnectionManager = websocket.app.state.ws_manager
    app_graph: Optional[CompiledStateGraph] = getattr(websocket.app.state, "app_graph", None)
    config: RunnableConfig = websocket.app.state.config

    user_text = payload.get("content", "").strip()
    if not user_text:
        return

    if app_graph is None:
        print("⚠️ [WS] Mensaje recibido pero el motor de razonamiento (app_graph) no está inicializado.")
        await ws_manager.send_personal({
            "type": "assistant_message",
            "content": "El motor de razonamiento se está inicializando o no está disponible en este momento. Por favor, intente de nuevo en unos segundos.",
        }, websocket)
        return

    print(f"📥 [WS User]: {user_text}")

    # Avisamos al frontend que Jarvis está procesando
    await ws_manager.send_personal({
        "type": "status",
        "state": "THINKING",
    }, websocket)

    try:
        state: AgentState = {
            "messages": [HumanMessage(content=user_text)],
            "correlation_id": str(uuid.uuid4()),
        }

        # Ejecución en el Grafo de LangGraph
        result = await app_graph.ainvoke(state, config=config)
        last_msg = result["messages"][-1]
        assistant_text = last_msg.content if isinstance(last_msg.content, str) else ""

        print(f"🤖 [WS Jarvis]: {assistant_text[:80]}...")

        # Enviamos la respuesta limpia al frontend
        await ws_manager.send_personal({
            "type": "assistant_message",
            "content": assistant_text,
        }, websocket)

    except Exception as err:
        print(f"❌ Error en ejecución de grafo: {err}")
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
async def websocket_endpoint(websocket: WebSocket):
    """Endpoint principal de WebSockets con delegación mediante Dispatcher."""
    ws_manager: Optional[WebSocketConnectionManager] = getattr(
        websocket.app.state, "ws_manager", None
    )
    runtime: Optional[AgentRuntime] = getattr(websocket.app.state, "runtime", None)

    if ws_manager is None:
        await websocket.close(code=1011, reason="Servidor no inicializado.")
        return

    await ws_manager.connect(websocket)

    # Enviamos saludo y estado inicial
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
            except Exception:
                continue

            if not isinstance(msg, dict):
                continue

            msg_type = msg.get("type", "")
            handler = MESSAGE_DISPATCHER.get(msg_type)
            if handler:
                await handler(websocket, msg)
            else:
                print(f"⚠️ [WebSocket] Mensaje no reconocido o sin manejador: '{msg_type}'")

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        print(f"⚠️ [WebSocket] Error en sesión: {e}")
        ws_manager.disconnect(websocket)
