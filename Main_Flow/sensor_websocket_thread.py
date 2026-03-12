"""
SensorWebSocketThread — listens for sensor UDP on a DEDICATED port (default 9000).
Control commands use port 8888. These must NOT share a port.

Arduino should send sensor data to port 9000:
  UDP packet format:  "HUM:65.3"  or  "CUR:2.1"
"""

import threading
import asyncio
import websockets
import socket
import json


class SensorWebSocketThread(threading.Thread):

    def __init__(self, ws_port=8765, udp_port=9000):
        # NOTE: udp_port is now 9000, NOT 8888.
        # 8888 is reserved exclusively for thruster/claw control commands.
        super().__init__(daemon=True, name="SensorWSThread")
        self.ws_port = ws_port
        self.udp_port = udp_port
        self.connected_clients: set = set()
        self.running = True
        self._loop: asyncio.AbstractEventLoop | None = None

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("", udp_port))
        self.sock.setblocking(False)
        print(f"[SensorWS] UDP sensor listener bound to port {udp_port}")
        print(f"[SensorWS] NOTE: Thruster control is on port 8888 (separate)")

    def run(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._main())
        except Exception as e:
            print(f"[SensorWS] Server error: {e}")
        finally:
            self._loop.close()

    async def _main(self):
        async with websockets.serve(self._handle_client, "0.0.0.0", self.ws_port):
            print(
                f"[SensorWS] WebSocket server on ws://0.0.0.0:{self.ws_port}")
            await self._udp_reader()

    async def _udp_reader(self):
        loop = asyncio.get_event_loop()
        while self.running:
            try:
                data, addr = await loop.run_in_executor(None, self._recv_udp)
            except Exception:
                await asyncio.sleep(0.01)
                continue

            if data is None:
                await asyncio.sleep(0.01)
                continue

            try:
                text = data.decode(errors="ignore").strip()
            except Exception:
                await asyncio.sleep(0.01)
                continue

            payload = self._parse(text, addr)
            if payload and self.connected_clients:
                msg = json.dumps(payload)
                dead = set()
                for client in set(self.connected_clients):
                    try:
                        await client.send(msg)
                    except Exception:
                        dead.add(client)
                for c in dead:
                    self.connected_clients.discard(c)

            await asyncio.sleep(0.01)

    def _recv_udp(self):
        try:
            return self.sock.recvfrom(1024)
        except BlockingIOError:
            return None, None
        except OSError:
            # Socket was closed (shutdown)
            return None, None
        except Exception as e:
            print(f"[SensorWS] UDP recv error: {e}")
            return None, None

    def _parse(self, msg: str, addr) -> dict | None:
        """
        Supported formats from Arduino:
          HUM:<float>   e.g. "HUM:65.3"
          CUR:<float>   e.g. "CUR:2.14"
        """
        if msg.startswith("HUM:"):
            try:
                return {"humidity": round(float(msg[4:]), 2)}
            except ValueError:
                pass
        elif msg.startswith("CUR:"):
            try:
                return {"current": round(float(msg[4:]), 3)}
            except ValueError:
                pass
        else:
            # Log unknown messages so you can debug new sensor formats
            print(f"[SensorWS] Unknown sensor message from {addr}: {msg!r}")
        return None

    async def _handle_client(self, websocket):
        self.connected_clients.add(websocket)
        print(f"[SensorWS] Client connected: {websocket.remote_address} "
              f"({len(self.connected_clients)} total)")
        try:
            await websocket.wait_closed()
        except Exception:
            pass
        finally:
            self.connected_clients.discard(websocket)
            print(f"[SensorWS] Client disconnected "
                  f"({len(self.connected_clients)} remaining)")

    def stop(self):
        self.running = False
        try:
            self.sock.close()
        except Exception:
            pass
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        print("[SensorWS] Stopped")
