import asyncio, sys

async def test():
    import websockets, json
    url = "wss://telemetry-project-theta.vercel.app/telemetry/ws"
    try:
        async with websockets.connect(url) as ws:
            for i in range(3):
                msg = await ws.recv()
                data = json.loads(msg)
                print("Received:", data)
    except Exception as e:
        print("Error:", e)
        sys.exit(1)

asyncio.run(test())
