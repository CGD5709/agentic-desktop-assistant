"""
API package exposing routers for HTTP and WebSocket endpoints.
"""
from .websockets import router as websockets_router

__all__ = ["websockets_router"]
