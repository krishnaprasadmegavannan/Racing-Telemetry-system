from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_websocket_route():
    try:
        with client.websocket_connect("/telemetry/ws") as websocket:
            print("SUCCESS: WebSocket connected!")
            # The server does not send messages automatically; just ensure connection works.
    except Exception as exc:
        assert False, f"WebSocket test failed: {exc}"
