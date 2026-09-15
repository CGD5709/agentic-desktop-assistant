import json
from typing import Any, Dict, List
from fastapi import WebSocket

from logger import get_logger

logger = get_logger("reasoning_engine.connection_manager")


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
        logger.info("WebSocket client connected. Active sessions: %d", len(self.active_connections))

    def disconnect(self, websocket: WebSocket) -> None:
        """
        Unregister a disconnected WebSocket session.

        Args:
            websocket: The WebSocket connection instance to remove.
        """
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info("WebSocket client disconnected. Active sessions: %d", len(self.active_connections))

    async def send_personal(self, message: Dict[str, Any], websocket: WebSocket) -> bool:
        """
        Serialize and dispatch a JSON payload to a specific client.

        Args:
            message: Dictionary payload to serialize and transmit.
            websocket: Target WebSocket connection.

        Returns:
            bool: True if sent successfully, False otherwise.
        """
        try:
            if hasattr(websocket, "client_state") and websocket.client_state.name != "CONNECTED":
                self.disconnect(websocket)
                return False
            await websocket.send_text(json.dumps(message))
            return True
        except Exception:
            self.disconnect(websocket)
            return False

    async def broadcast(self, message: Dict[str, Any]) -> None:
        """
        Broadcast a serialized JSON payload to all active clients, automatically
        pruning dead or broken connections encountered during transmission.

        Args:
            message: Dictionary payload to broadcast.
        """
        payload_text = json.dumps(message)
        dead_connections: List[WebSocket] = []

        for connection in list(self.active_connections):
            try:
                await connection.send_text(payload_text)
            except Exception:
                dead_connections.append(connection)

        for dead_conn in dead_connections:
            self.disconnect(dead_conn)

    async def send_or_broadcast(
        self, message: Dict[str, Any], websocket: WebSocket | None = None
    ) -> None:
        """
        Attempt to send to the specific client session. If disconnected or failed,
        fallback to broadcasting to all currently active sessions.
        """
        if websocket is not None and websocket in self.active_connections:
            success = await self.send_personal(message, websocket)
            if success:
                return
        await self.broadcast(message)
