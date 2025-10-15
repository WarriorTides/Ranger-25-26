import asyncio
import json
import serial
import websockets

ser = serial.Serial('/dev/ttyUSB0', 9600, timeout=1)

async def handler(websocket):
    print("Client connected")
    try:
        while True:
            line = ser.readline().decode().strip()
            if line.startswith("HUMIDITY:"):
                humidity = float(line.split(":")[1])
                data = {"humidity": humidity}
                await websocket.send(json.dumps(data))
                print(f"Sent: {data}")
            await asyncio.sleep(0.2)
    except websockets.ConnectionClosed:
        print("Client disconnected")

async def main():
    async with websockets.serve(handler, "0.0.0.0", 8765):
        print("Sensor WebSocket server running on ws://0.0.0.0:8765")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
