"""Compatibility entry point: the production WebSocket endpoint is served by FastAPI."""
from websocket.manager import manager

__all__ = ["manager"]
