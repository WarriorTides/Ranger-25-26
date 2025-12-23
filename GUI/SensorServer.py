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

print(f"UDP socket bound to port {UDP_PORT}")
print(f"Waiting for connections...")

connected_clients = set()

async def handler(websocket):
    connected_clients.add(websocket)
    client_addr = websocket.remote_address
    print(f"WebSocket client connected from {client_addr} (Total clients: {len(connected_clients)})")
    
    try:
        while True:
            try:
                data, addr = sock.recvfrom(1024)
                msg = data.decode().strip()
                print(f"UDP from {addr}: '{msg}'")

                payload = None

                # Handle HUMIDITY
                if msg.startswith("HUM:"):
                    try:
                        humidity = float(msg.split(":")[1])
                        payload = {"humidity": humidity}
                        print(f"Parsed humidity: {payload}")
                    except Exception as e:
                        print(f"BAD HUMIDITY: {msg} - {e}")

                # Handle CURRENT
                elif msg.startswith("CUR:"):
                    try:
                        current = float(msg.split(":")[1])
                        payload = {"current": current}
                        print(f"Parsed current: {payload}")
                    except Exception as e:
                        print(f"BAD CURRENT: {msg} - {e}")

                # Send to ALL connected clients
                if payload:
                    json_msg = json.dumps(payload)
                    for client in connected_clients.copy():
                        try:
                            await client.send(json_msg)
                            print(f"Sent to client: {json_msg}")
                        except Exception as e:
                            print(f"Failed to send to client: {e}")
                            connected_clients.discard(client)

            except socket.timeout:
                pass

            await asyncio.sleep(0.05)

    except websockets.ConnectionClosed:
        print(f"WebSocket client {client_addr} disconnected")
    finally:
        connected_clients.discard(websocket)
        print(f"Total clients: {len(connected_clients)}")

async def main():
    async with websockets.serve(handler, "0.0.0.0", WEBSOCKET_PORT):
        print(f"WebSocket server running on ws://0.0.0.0:{WEBSOCKET_PORT}")
        print(f"Ready to accept connections...")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())