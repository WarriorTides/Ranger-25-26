import threading
import asyncio
import websockets
import socket
import json


class SensorWebSocketThread(threading.Thread):
    """
    Runs a WebSocket server that receives sensor data via UDP from Arduino
    and forwards it to connected WebSocket clients (like the GUI).
    Runs in a separate thread with its own asyncio event loop.
    """

    def __init__(self, ws_port=8765, udp_port=8888):
        super().__init__(daemon=True)
        self.ws_port = ws_port
        self.udp_port = udp_port
        self.connected_clients = set()
        self.running = True

        # UDP socket for receiving sensor data from Arduino
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("", udp_port))
        self.sock.settimeout(0.1)

        print(f"Sensor UDP listener bound to port {udp_port}")

    def run(self):
        """Start the thread - creates new event loop and runs WebSocket server"""
        print(f"Starting WebSocket server on port {self.ws_port}")

        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Run the WebSocket server
        try:
            loop.run_until_complete(self.start_server())
        except Exception as e:
            print(f"Sensor WebSocket server error: {e}")
        finally:
            loop.close()

    async def start_server(self):
        """Start the WebSocket server and run forever"""
        async with websockets.serve(self.handle_client, "0.0.0.0", self.ws_port):
            print(
                f"Sensor WebSocket server running on ws://0.0.0.0:{self.ws_port}")
            await asyncio.Future()  # Run forever

    async def handle_client(self, websocket):
        """Handle a connected WebSocket client"""
        self.connected_clients.add(websocket)
        client_info = websocket.remote_address
        print(
            f"Sensor WS client connected from {client_info} ({len(self.connected_clients)} total)")

        try:
            while self.running:
                # Receive sensor data from Arduino via UDP
                try:
                    data, addr = self.sock.recvfrom(1024)
                    msg = data.decode().strip()
                    print(f"Sensor data from {addr}: {msg}")

                    payload = None

                    # Parse humidity data
                    if msg.startswith("HUM:"):
                        try:
                            humidity = float(msg[4:])
                            payload = {"humidity": humidity}
                            print(f"  Humidity = {humidity}%")
                        except ValueError:
                            print(f"  Bad humidity value: {msg}")

                    # Parse current data
                    elif msg.startswith("CUR:"):
                        try:
                            current = float(msg[4:])
                            payload = {"current": current}
                            print(f"  Current = {current}A")
                        except ValueError:
                            print(f"  Bad current value: {msg}")

                    # Forward to all connected WebSocket clients
                    if payload:
                        json_msg = json.dumps(payload)

                        # Send to all clients, track dead connections
                        dead_clients = []
                        for client in self.connected_clients:
                            try:
                                await client.send(json_msg)
                            except Exception as e:
                                print(f"Failed to send to client: {e}")
                                dead_clients.append(client)

                        # Remove dead connections
                        for dead in dead_clients:
                            self.connected_clients.remove(dead)
                            print(
                                f"Removed dead client ({len(self.connected_clients)} remaining)")

                except socket.timeout:
                    # No data received, continue
                    pass
                except Exception as e:
                    print(f"Error receiving sensor data: {e}")

                # Small delay to prevent busy-waiting
                await asyncio.sleep(0.02)

        except websockets.ConnectionClosed:
            print(f"Sensor WS client {client_info} disconnected")
        except Exception as e:
            print(f"Error in sensor client handler: {e}")
        finally:
            self.connected_clients.discard(websocket)
            print(f"Client removed ({len(self.connected_clients)} remaining)")

    def stop(self):
        """Stop the WebSocket server"""
        self.running = False
        self.sock.close()
