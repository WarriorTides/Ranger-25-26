import asyncio
import websockets
import json
import random

async def handler(websocket):
    print("Client connected")
    try:
        while True:
            data = {
                "humidity": round(random.uniform(100, 130), 1),
                "current": round(random.uniform(0, 5), 1)
            }
            await websocket.send(json.dumps(data))
            print(f"Sent: {data}")
            
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=0.1)
                print(f"Received from client: {message}")
            except asyncio.TimeoutError:
                pass

            await asyncio.sleep(1)
    except websockets.ConnectionClosed:
        print("Client disconnected")

async def main():
    async with websockets.serve(handler, "localhost", 8765):
        print("Dummy WebSocket server started at ws://localhost:8765")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
