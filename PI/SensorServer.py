import asyncio
import websockets
import json
from ArdInterface import ArduinoInterface

arduino = ArduinoInterface()
PORT = 8765
CLIENTS = set()

async def sensor_handler(websocket, path):
    CLIENTS.add(websocket)
    try:
        while True:
            data = arduino.read_sensors()
            if data:
                message = json.dumps(data)
                await websocket.send(message)
            await asyncio.sleep(0.05) 
    except websockets.ConnectionClosed:
        pass
    finally:
        CLIENTS.remove(websocket)

async def main():
    async with websockets.serve(sensor_handler, "0.0.0.0", PORT):
        print(f"Sensor WebSocket server running on port {PORT}")
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
