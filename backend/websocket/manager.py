import asyncio
from fastapi import WebSocket


class ConnectionManager:

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            try:
                self.active_connections.remove(websocket)
            except ValueError:
                pass

    async def broadcast(self, data: dict):
        if not self.active_connections:
            return

        async def _safe_send(ws: WebSocket):
            try:
                await ws.send_json(data)
                return None
            except Exception:
                return ws

        results = await asyncio.gather(
            *[_safe_send(ws) for ws in list(self.active_connections)],
            return_exceptions=True
        )

        for failed_ws in results:
            if isinstance(failed_ws, WebSocket):
                self.disconnect(failed_ws)


manager = ConnectionManager()