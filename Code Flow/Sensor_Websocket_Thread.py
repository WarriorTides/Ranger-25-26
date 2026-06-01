# """
# SWEAR TO GOD IF THIS DOESNT WORK ... PLEASE BRO ... LITERALLY PLEASE..CAUSE WHY DID THIS GET CHOSEN .. GENUNILY WHYY .. SHUT UP jason....no YOU shut up kashish...STOP TYPING ON MY FILES dumbasses
# """

# import threading
# import asyncio
# import websockets
# import socket
# import json


# class SensorWebSocketThread(threading.Thread):

#     def __init__(self, ws_port=8765, udp_port=8888):
#         super().__init__(daemon=True, name="SensorWSThread")
#         self.ws_port = ws_port
#         self.udp_port = udp_port
#         self.connected_clients: set = set()
#         self.running = True
#         self._loop: asyncio.AbstractEventLoop | None = None

#         self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#         self.sock.bind(("", udp_port))
#         self.sock.setblocking(False)
#         print(f"[SensorWS] UDP listener bound to port {udp_port}")

#     def run(self):
#         self._loop = asyncio.new_event_loop()
#         asyncio.set_event_loop(self._loop)
#         try:
#             self._loop.run_until_complete(self._main())
#         except Exception as e:
#             print(f"[SensorWS] Server error: {e}")
#         finally:
#             self._loop.close()

#     async def _main(self):
#         async with websockets.serve(self._handle_client, "0.0.0.0", self.ws_port):
#             print(
#                 f"[SensorWS] WebSocket server on ws://0.0.0.0:{self.ws_port}")
#             await self._udp_reader()

#     async def _udp_reader(self):
#         loop = asyncio.get_event_loop()
#         while self.running:
#             try:
#                 data, addr = await loop.run_in_executor(None, self._recv_udp)
#             except Exception:
#                 await asyncio.sleep(0.01)
#                 continue

#             if data is None:
#                 await asyncio.sleep(0.01)
#                 continue

#             payload = self._parse(data.decode().strip(), addr)
#             if payload and self.connected_clients:
#                 msg = json.dumps(payload)
#                 dead = set()
#                 for client in set(self.connected_clients):
#                     try:
#                         await client.send(msg)
#                     except Exception:
#                         dead.add(client)
#                 for c in dead:
#                     self.connected_clients.discard(c)

#             await asyncio.sleep(0.01)

#     def _recv_udp(self):
#         try:
#             return self.sock.recvfrom(1024)
#         except BlockingIOError:
#             return None, None
#         except Exception as e:
#             print(f"[SensorWS] UDP recv error: {e}")
#             return None, None

#     def _parse(self, msg: str, addr) -> dict | None:
#         if msg.startswith("HUM:"):
#             try:
#                 return {"humidity": float(msg[4:])}
#             except ValueError:
#                 pass
#         elif msg.startswith("CUR:"):
#             try:
#                 return {"current": float(msg[4:])}
#             except ValueError:
#                 pass
#         return None

#     async def _handle_client(self, websocket):
#         self.connected_clients.add(websocket)
#         print(f"[SensorWS] Client connected: {websocket.remote_address} "
#               f"({len(self.connected_clients)} total)")
#         try:
#             await websocket.wait_closed()
#         except Exception:
#             pass
#         finally:
#             self.connected_clients.discard(websocket)
#             print(f"[SensorWS] Client disconnected "
#                   f"({len(self.connected_clients)} remaining)")

#     def stop(self):
#         self.running = False
#         try:
#             self.sock.close()
#         except Exception:
#             pass
#         if self._loop and self._loop.is_running():
#             self._loop.call_soon_threadsafe(self._loop.stop)
#         print("[SensorWS] Stopped")


# ----


import threading
import asyncio
import websockets
import json


class _UDPProtocol(asyncio.DatagramProtocol):
    def __init__(self, on_data):
        self._on_data = on_data

    def datagram_received(self, data, addr):
        self._on_data(data, addr)

    def error_received(self, exc):
        print(f"[SensorWS] UDP error: {exc}")


class SensorWebSocketThread(threading.Thread):

    def __init__(self, ws_port=8765, udp_port=8888):
        super().__init__(daemon=True, name="SensorWSThread")
        self.ws_port = ws_port
        self.udp_port = udp_port
        self.connected_clients: set = set()
        self.running = True
        self._loop: asyncio.AbstractEventLoop | None = None

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
        loop = asyncio.get_event_loop()

        # Native async UDP — no executor, no thread pool exhaustion
        transport, _ = await loop.create_datagram_endpoint(
            lambda: _UDPProtocol(self._on_udp_data),
            local_addr=("0.0.0.0", self.udp_port),
        )
        print(f"[SensorWS] UDP listener on port {self.udp_port}")

        try:
            async with websockets.serve(self._handle_client, "0.0.0.0", self.ws_port):
                print(
                    f"[SensorWS] WebSocket server on ws://0.0.0.0:{self.ws_port}")
                # Keep running until stopped
                while self.running:
                    await asyncio.sleep(0.5)
        finally:
            transport.close()

    def _on_udp_data(self, data: bytes, addr):
        """Called directly by the event loop — zero executor overhead."""
        payload = self._parse(data.decode(errors="replace").strip(), addr)
        if payload and self.connected_clients:
            msg = json.dumps(payload)
            # Schedule the async broadcast on the running loop
            asyncio.run_coroutine_threadsafe(
                self._broadcast(msg), self._loop
            )

    async def _broadcast(self, msg: str):
        dead = set()
        for client in set(self.connected_clients):
            try:
                await client.send(msg)
            except Exception:
                dead.add(client)
        for c in dead:
            self.connected_clients.discard(c)

    def _parse(self, msg: str, addr) -> dict | None:
        if msg.startswith("HUM:"):
            try:
                return {"humidity": float(msg[4:])}
            except ValueError:
                pass
        elif msg.startswith("CUR:"):
            try:
                return {"current": float(msg[4:])}
            except ValueError:
                pass
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
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        print("[SensorWS] Stopped")
