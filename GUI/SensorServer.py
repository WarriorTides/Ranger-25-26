# SensorServer.py
import asyncio
import json
import socket
import websockets

UDP_PORT = 8888
WEBSOCKET_PORT = 8765

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("", UDP_PORT))
sock.settimeout(0.1)

async def handler(websocket):
    print("WebSocket client connected")
    try:
        while True:
            try:
                data, addr = sock.recvfrom(1024)
                msg = data.decode().strip()

                if msg.startswith("HUM:"):
                    humidity = float(msg.split(":")[1])
                    payload = {"humidity": humidity}
                    await websocket.send(json.dumps(payload))
                    print(f"Sent humidity: {payload}")

                elif msg.startswith("CUR:"):
                    current = float(msg.split(":")[1])
                    payload = {"current": current}
                    await websocket.send(json.dumps(payload))
                    print(f"Sent current: {payload}")

            except socket.timeout:
                pass

            await asyncio.sleep(0.05)

    except websockets.ConnectionClosed:
        print("WebSocket client disconnected")

async def main():
    async with websockets.serve(handler, "0.0.0.0", WEBSOCKET_PORT):
        print(f"Sensor WebSocket server running on ws://0.0.0.0:{WEBSOCKET_PORT}")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
