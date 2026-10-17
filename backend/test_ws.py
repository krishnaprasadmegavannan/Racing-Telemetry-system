from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

print("Testing WebSocket route...")

try:
    with client.websocket_connect("/telemetry/ws") as websocket:
        print("SUCCESS: WebSocket connected!")

        # The current handler waits for client messages.
        # Receiving telemetry is a separate broadcast operation.
        print("The WebSocket handshake succeeded.")

except Exception as exc:
    print("WebSocket test failed:", repr(exc))