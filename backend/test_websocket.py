import asyncio
import websockets


async def test_websocket():

    uri = "ws://127.0.0.1:8000/telemetry/ws"

    async with websockets.connect(uri) as websocket:

        print("WebSocket connected.")
        print("Waiting for telemetry...")
        print()

        while True:

            message = await websocket.recv()

            print("LIVE TELEMETRY:")
            print(message)
            print()


asyncio.run(test_websocket())