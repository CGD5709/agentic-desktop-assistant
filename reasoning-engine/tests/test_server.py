"""
Unit tests for the Layered Architecture Reasoning Engine server.
Validates Dependency Injection via app.state, the WebSocket Dispatcher pattern in api/websockets.py,
and the encapsulated RabbitMQ listener factory in services/rabbitmq_listener.py.
"""
import json
from unittest.mock import AsyncMock, MagicMock
import pytest
from fastapi.testclient import TestClient

from api.websockets import handle_ping_message, handle_user_message
from main import app
from services.connection_manager import WebSocketConnectionManager
from services.rabbitmq_listener import (
    convert_execution_tools_to_openai_format,
    create_rabbitmq_message_handler,
)


@pytest.fixture
def test_app_state():
    """Configures isolated test state on app.state for testing endpoints and handlers."""
    mock_runtime = MagicMock()
    mock_runtime.dynamic_tools = [{"function": {"name": "test_tool"}}]
    mock_ws_manager = WebSocketConnectionManager()
    config = {"configurable": {"thread_id": "test-thread"}}

    app.state.runtime = mock_runtime
    app.state.ws_manager = mock_ws_manager
    app.state.config = config
    app.state.app_graph = None

    yield {
        "runtime": mock_runtime,
        "ws_manager": mock_ws_manager,
        "config": config,
    }


def test_health_check_starting_and_online(test_app_state):
    """Verify /health reflects STARTING when app_graph is None and ONLINE when compiled."""
    client = TestClient(app)

    # Initial state: app_graph is None
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "STARTING"
    assert data["tools_count"] == 1
    assert data["tools"] == ["test_tool"]

    # When app_graph is present
    app.state.app_graph = MagicMock()
    res2 = client.get("/health")
    assert res2.status_code == 200
    assert res2.json()["status"] == "ONLINE"


def test_websocket_ping_pong_dispatcher(test_app_state):
    """Verify that ping messages are routed by the dispatcher to handle_ping_message."""
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws:
        # Initial connection greeting
        greeting = ws.receive_json()
        assert greeting["type"] == "connected"
        assert greeting["tools"] == ["test_tool"]

        # Send ping
        ws.send_json({"type": "ping"})
        pong = ws.receive_json()
        assert pong["type"] == "pong"


def test_websocket_user_message_when_engine_not_ready(test_app_state):
    """Verify handle_user_message returns a courteous waiting message when app_graph is None."""
    app.state.app_graph = None
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws:
        greeting = ws.receive_json()
        assert greeting["type"] == "connected"

        ws.send_json({"type": "user_message", "content": "Hola Jarvis"})
        response = ws.receive_json()
        assert response["type"] == "assistant_message"
        assert "inicializando" in response["content"].lower()


def test_websocket_user_message_execution_flow(test_app_state):
    """Verify handle_user_message executes the LangGraph workflow and broadcasts status transitions."""
    mock_graph = AsyncMock()
    mock_msg = MagicMock()
    mock_msg.content = "Buenos días, señor. ¿En qué le ayudo?"
    mock_graph.ainvoke.return_value = {"messages": [mock_msg]}
    app.state.app_graph = mock_graph

    client = TestClient(app)
    with client.websocket_connect("/ws") as ws:
        greeting = ws.receive_json()
        assert greeting["type"] == "connected"

        ws.send_json({"type": "user_message", "content": "Hola"})

        # Expect THINKING status
        status_msg = ws.receive_json()
        assert status_msg["type"] == "status"
        assert status_msg["state"] == "THINKING"

        # Expect assistant message
        reply = ws.receive_json()
        assert reply["type"] == "assistant_message"
        assert reply["content"] == "Buenos días, señor. ¿En qué le ayudo?"

        # Expect IDLE status
        idle_msg = ws.receive_json()
        assert idle_msg["type"] == "status"
        assert idle_msg["state"] == "IDLE"

    # Verify ainvoke was called with state and config
    assert mock_graph.ainvoke.called
    call_args = mock_graph.ainvoke.call_args
    assert call_args[1]["config"] == app.state.config


def test_convert_execution_tools_to_openai_format():
    """Verify convert_execution_tools_to_openai_format maps tool specifications properly."""
    raw_tools = [
        {
            "name": "take_screenshot",
            "description": "Takes a screenshot of active display",
            "parameters": {"type": "object", "properties": {"format": {"type": "string"}}},
        }
    ]
    converted = convert_execution_tools_to_openai_format(raw_tools)
    assert len(converted) == 1
    assert converted[0]["type"] == "function"
    assert converted[0]["function"]["name"] == "take_screenshot"
    assert "parameters" in converted[0]["function"]


@pytest.mark.asyncio
async def test_rabbitmq_message_handler_factory():
    """Verify create_rabbitmq_message_handler updates dynamic_tools and broadcasts updates."""
    mock_runtime = MagicMock()
    mock_runtime.dynamic_tools = []
    mock_ws_manager = AsyncMock()

    handler = create_rabbitmq_message_handler(mock_runtime, mock_ws_manager)

    payload = {
        "payload": {
            "tools": [
                {
                    "name": "open_application",
                    "description": "Opens an app",
                    "parameters": {"type": "object", "properties": {}},
                }
            ]
        }
    }

    # Irrelevant routing key should be ignored
    await handler(json.dumps(payload), "system.other.key")
    assert len(mock_runtime.dynamic_tools) == 0

    # Matching routing key should update tools and broadcast
    await handler(json.dumps(payload), "system.discovery.execution_service")
    assert len(mock_runtime.dynamic_tools) == 1
    assert mock_runtime.dynamic_tools[0]["function"]["name"] == "open_application"
    assert mock_ws_manager.broadcast.called


def test_cors_allowed_and_blocked_origins():
    """Verify CORS middleware permits configured origins and rejects unauthorized origins."""
    client = TestClient(app)

    # Allowed origin (desktop-client on port 5173)
    res_allowed = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert res_allowed.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert res_allowed.headers.get("access-control-allow-credentials") == "true"

    # Unauthorized origin
    res_blocked = client.get("/health", headers={"Origin": "http://malicious-website.com"})
    assert res_blocked.headers.get("access-control-allow-origin") is None


def test_settings_cors_origins_parsing():
    """Verify Settings parses comma-separated strings and JSON strings correctly."""
    from config import Settings

    # Comma-separated string
    s1 = Settings(ALLOWED_ORIGINS="http://localhost:3000, http://localhost:5173")
    assert s1.ALLOWED_ORIGINS == ["http://localhost:3000", "http://localhost:5173"]

    # JSON array string
    s2 = Settings(ALLOWED_ORIGINS='["http://example.com"]')
    assert s2.ALLOWED_ORIGINS == ["http://example.com"]


def test_websocket_confirmation_response_dispatcher(test_app_state):
    """Verify that confirmation_response is routed to confirmation_manager."""
    client = TestClient(app)
    mock_runtime = test_app_state["runtime"]
    mock_conf_manager = MagicMock()
    mock_runtime.confirmation_manager = mock_conf_manager

    with client.websocket_connect("/ws") as ws:
        greeting = ws.receive_json()
        assert greeting["type"] == "connected"

        ws.send_json({
            "type": "confirmation_response",
            "confirmation_id": "conf-test-123",
            "confirmed": True,
        })

    mock_conf_manager.resolve_confirmation.assert_called_once_with("conf-test-123", True)

