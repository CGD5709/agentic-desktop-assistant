"""
WebSocket connection manager service for active client sessions.
"""
import json
from typing import Any, Dict, List
from fastapi import WebSocket


class WebSocketConnectionManager:
    """
    Manages active WebSocket client connections and message distribution.

    Provides safe connection registration, unregistration, single-client
    messaging, and broadcast dispatching with automatic dead connection pruning.
    """

    def __init__(self) -> None:
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """
        Accept an incoming WebSocket connection and register it in active sessions.

        Args:
            websocket: Incoming FastAPI WebSocket connection instance.
        """
        await websocket.accept()
        self.active_connections.append(websocket)
        # TODO: Replace print with a standardized logging framework (e.g., logging/structlog).
        print(f"🔌 [WebSocket] Client connected. Active sessions: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket) -> None:
        """
        Unregister a disconnected WebSocket session.

        Args:
            websocket: The WebSocket connection instance to remove.
        """
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            # TODO: Replace print with a standardized logging framework (e.g., logging/structlog).
            print(f"🔌 [WebSocket] Client disconnected. Active sessions: {len(self.active_connections)}")

    async def send_personal(self, message: Dict[str, Any], websocket: WebSocket) -> None:
        """
        Serialize and dispatch a JSON payload to a specific client.

        Args:
            message: Dictionary payload to serialize and transmit.
            websocket: Target WebSocket connection.
        """
        try:
            if hasattr(websocket, "client_state") and websocket.client_state.name != "CONNECTED":
                self.disconnect(websocket)
                return
            await websocket.send_text(json.dumps(message))
        except Exception:
            self.disconnect(websocket)

    async def broadcast(self, message: Dict[str, Any]) -> None:
        """
        Broadcast a serialized JSON payload to all active clients, automatically
        pruning dead or broken connections encountered during transmission.

        Args:
            message: Dictionary payload to broadcast.
        """
        payload_text = json.dumps(message)
        dead_connections: List[WebSocket] = []

        for connection in self.active_connections:
            try:
                await connection.send_text(payload_text)
            except Exception:
                dead_connections.append(connection)

        for dead_conn in dead_connections:
            self.disconnect(dead_conn)
