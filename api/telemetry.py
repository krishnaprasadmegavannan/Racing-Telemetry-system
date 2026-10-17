import asyncio
import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/telemetry", tags=["telemetry"])

async def event_stream():
    """Async generator yielding Server‑Sent Events (SSE) formatted JSON lines.
    Each line is prefixed with `data:` and ends with a double newline as required by SSE.
    """
    counter = 0
    while True:
        payload = {"timestamp": asyncio.get_event_loop().time(), "value": counter}
        # SSE format: data: <json>\n\n
        yield f"data: {json.dumps(payload)}\n\n"
        counter += 1
        await asyncio.sleep(1)

@router.get("/stream", response_class=StreamingResponse)
async def stream_data():
    """Streaming endpoint using Server‑Sent Events (text/event-stream)."""
    return StreamingResponse(event_stream(), media_type="text/event-stream")
