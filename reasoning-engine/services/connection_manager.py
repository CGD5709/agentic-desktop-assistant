"""
WebSocket connection manager service for active client sessions.
"""
import json
from typing import Any, Dict, List
from fastapi import WebSocket


class WebSocketConnectionManager:
    """Administra las conexiones de clientes WebSocket activos."""

    def __init__(self) -> None:
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Acepta la conexión entrante y la registra en el listado de conexiones activas."""
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"🔌 [WebSocket] Cliente conectado. Activos: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket) -> None:
        """Remueve la conexión desconectada de la lista de clientes activos."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            print(f"🔌 [WebSocket] Cliente desconectado. Activos: {len(self.active_connections)}")

    async def send_personal(self, message: Dict[str, Any], websocket: WebSocket) -> None:
        """Envía un payload serializado en JSON a un cliente específico."""
        await websocket.send_text(json.dumps(message))

    async def broadcast(self, message: Dict[str, Any]) -> None:
        """Difunde un payload a todos los clientes WebSocket activos, purgando conexiones inactivas."""
        dead_connections: List[WebSocket] = []
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                dead_connections.append(connection)
        for dc in dead_connections:
            self.disconnect(dc)
