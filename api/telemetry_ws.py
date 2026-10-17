import asyncio
import logging
from fastapi import APIRouter, WebSocket

# Configure module-level logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telemetry", tags=["telemetry"])

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    counter = 0
    try:
        while True:
            # Obtain a reliable timestamp regardless of event loop availability
            try:
                timestamp = asyncio.get_running_loop().time()
            except Exception:
                import time as _time
                timestamp = _time.time()

            payload = {
                "type": "telemetry_update",
                "raw": {
                    "gps": {"speed": counter},
                    "vehicle_can": {"rpm": counter * 10}
                },
                "timestamp": timestamp,
            }
            await websocket.send_json(payload)
            counter += 1
            await asyncio.sleep(1)
    except Exception as e:
        logger.error("WebSocket connection closed or error: %s", e)
        await websocket.close()
