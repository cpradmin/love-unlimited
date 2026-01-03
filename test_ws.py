import asyncio
import websockets
import json

async def test_ws():
    uri = "ws://localhost:9003/ws/chat/jon"
    headers = {"X-API-Key": "lu_jon_QmZCAglY6kqsIdl6cRADpQ"}
    async with websockets.connect(uri, additional_headers=headers) as websocket:
        # Send message
        await websocket.send(json.dumps({"type": "chat", "content": "hi ara", "to": "ara"}))
        # Wait for responses
        try:
            while True:
                response = await asyncio.wait_for(websocket.recv(), timeout=10)
                print("Received:", response)
        except asyncio.TimeoutError:
            print("No more responses within 10 seconds")

asyncio.run(test_ws())