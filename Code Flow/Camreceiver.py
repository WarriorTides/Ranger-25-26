# # import socket
# # import struct
# # import cv2
# # import numpy as np
# # import threading
# # import queue
# # import time

# # from PyQt6.QtCore import QObject, pyqtSignal, Qt

# # HEADER_FMT = ">BI"
# # HEADER_SIZE = struct.calcsize(HEADER_FMT)


# # class _PerCamDecoder(threading.Thread):
# #     """One decode thread per camera — frames never mix between cameras."""

# #     def __init__(self, cam_id: int, on_frame):
# #         super().__init__(daemon=True, name=f"DecodeThread-cam{cam_id}")
# #         self.cam_id = cam_id
# #         self._on_frame = on_frame          # callable(cam_id, frame_rgb)
# #         self._queue: queue.Queue = queue.Queue(maxsize=2)
# #         self._running = True

# #     def enqueue(self, jpg_bytes: bytes):
# #         try:
# #             self._queue.put_nowait(jpg_bytes)
# #         except queue.Full:
# #             # drop oldest, push newest
# #             try:
# #                 self._queue.get_nowait()
# #             except queue.Empty:
# #                 pass
# #             try:
# #                 self._queue.put_nowait(jpg_bytes)
# #             except queue.Full:
# #                 pass

# #     def run(self):
# #         while self._running:
# #             try:
# #                 jpg_bytes = self._queue.get(timeout=0.1)
# #             except queue.Empty:
# #                 continue

# #             if len(jpg_bytes) < 100:
# #                 continue

# #             try:
# #                 nparr = np.frombuffer(jpg_bytes, np.uint8)
# #                 frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
# #                 if frame is not None:
# #                     frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
# #                     self._on_frame(self.cam_id, frame_rgb)
# #             except Exception as e:
# #                 print(f"[CamReceiver] Decode error cam {self.cam_id}: {e}")

# #     def stop(self):
# #         self._running = False


# # class CameraReceiver(QObject):
# #     frame_received = pyqtSignal(int, object)

# #     SOCKET_RCVBUF = 2 * 1024 * 1024
# #     READ_SIZE = 65536

# #     def __init__(self, ports=None):
# #         super().__init__()
# #         self.ports = ports or [5005, 5006, 5007]
# #         self.sockets: list[socket.socket] = []

# #         # One decoder per camera (keyed by cam_id = port index + 1)
# #         self._decoders: dict[int, _PerCamDecoder] = {}
# #         for i, port in enumerate(self.ports):
# #             cam_id = i + 1
# #             decoder = _PerCamDecoder(cam_id, self._on_frame_ready)
# #             decoder.start()
# #             self._decoders[cam_id] = decoder

# #             sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# #             sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
# #             sock.setsockopt(socket.SOL_SOCKET,
# #                             socket.SO_RCVBUF, self.SOCKET_RCVBUF)
# #             sock.bind(("0.0.0.0", port))
# #             sock.setblocking(False)
# #             self.sockets.append(sock)
# #             print(f"[CamReceiver] Listening on UDP port {port} (cam {cam_id})")

# #         print("[CamReceiver] Per-camera decode threads started")

# #     # Called from background decode threads — must be thread-safe.
# #     # PyQt6 queued signal emission is thread-safe.
# #     def _on_frame_ready(self, cam_id: int, frame_rgb):
# #         self.frame_received.emit(cam_id, frame_rgb)

# #     def poll(self):
# #         """Drain sockets — called from QTimer on main thread."""
# #         for i, sock in enumerate(self.sockets):
# #             for _ in range(20):
# #                 try:
# #                     packet, _ = sock.recvfrom(self.READ_SIZE)
# #                 except BlockingIOError:
# #                     break
# #                 except OSError:
# #                     break
# #                 except Exception as e:
# #                     print(
# #                         f"[CamReceiver] Socket error port {self.ports[i]}: {e}")
# #                     break

# #                 if len(packet) < HEADER_SIZE:
# #                     continue

# #                 cam_id, payload_len = struct.unpack(
# #                     HEADER_FMT, packet[:HEADER_SIZE])
# #                 jpg_bytes = packet[HEADER_SIZE:]

# #                 if len(jpg_bytes) != payload_len:
# #                     continue

# #                 decoder = self._decoders.get(cam_id)
# #                 if decoder:
# #                     decoder.enqueue(jpg_bytes)

# #     def stop(self):
# #         for decoder in self._decoders.values():
# #             decoder.stop()
# #         for sock in self.sockets:
# #             try:
# #                 sock.close()
# #             except Exception:
# #                 pass
# #         print("[CamReceiver] Closed")

# #     # Legacy alias used in MainWindow.closeEvent
# #     def close(self):
# #         self.stop()


# import socket
# import struct
# import select
# import cv2
# import numpy as np
# import threading
# import queue
# import time

# from PyQt6.QtCore import QObject, pyqtSignal

# HEADER_FMT = ">BI"
# HEADER_SIZE = struct.calcsize(HEADER_FMT)


# class _PerCamDecoder(threading.Thread):
#     """One decode thread per camera — frames never mix between cameras."""

#     def __init__(self, cam_id: int, on_frame):
#         super().__init__(daemon=True, name=f"DecodeThread-cam{cam_id}")
#         self.cam_id = cam_id
#         self._on_frame = on_frame
#         self._queue: queue.Queue = queue.Queue(maxsize=2)
#         self._running = True

#     def enqueue(self, jpg_bytes: bytes):
#         try:
#             self._queue.put_nowait(jpg_bytes)
#         except queue.Full:
#             try:
#                 self._queue.get_nowait()
#             except queue.Empty:
#                 pass
#             try:
#                 self._queue.put_nowait(jpg_bytes)
#             except queue.Full:
#                 pass

#     def run(self):
#         while self._running:
#             try:
#                 jpg_bytes = self._queue.get(timeout=0.1)
#             except queue.Empty:
#                 continue

#             if len(jpg_bytes) < 100:
#                 continue

#             try:
#                 nparr = np.frombuffer(jpg_bytes, np.uint8)
#                 frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
#                 if frame is not None:
#                     frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
#                     self._on_frame(self.cam_id, frame_rgb)
#             except Exception as e:
#                 print(f"[CamReceiver] Decode error cam {self.cam_id}: {e}")

#     def stop(self):
#         self._running = False


# class _SocketPollThread(threading.Thread):
#     """
#     Dedicated background thread that drains all UDP sockets using select().
#     Keeps blocking I/O entirely off the Qt main thread, eliminating the
#     primary source of lag and freeze.
#     """

#     def __init__(self, sockets: list, ports: list, decoders: dict):
#         super().__init__(daemon=True, name="SocketPollThread")
#         self._sockets = sockets
#         self._ports = ports
#         self._decoders = decoders
#         self._running = True

#     def run(self):
#         while self._running:
#             try:
#                 # Block until at least one socket has data, timeout=0.05s
#                 # so the loop can check _running periodically.
#                 readable, _, _ = select.select(self._sockets, [], [], 0.05)
#             except Exception as e:
#                 print(f"[CamReceiver] select error: {e}")
#                 time.sleep(0.05)
#                 continue

#             for sock in readable:
#                 # Drain up to 5 packets per ready socket per wakeup.
#                 # Smaller than before (was 20) — prevents one socket
#                 # monopolising the loop when there is a burst.
#                 for _ in range(5):
#                     try:
#                         packet, _ = sock.recvfrom(65536)
#                     except BlockingIOError:
#                         break
#                     except OSError:
#                         break
#                     except Exception as e:
#                         print(f"[CamReceiver] recv error: {e}")
#                         break

#                     if len(packet) < HEADER_SIZE:
#                         continue

#                     cam_id, payload_len = struct.unpack(
#                         HEADER_FMT, packet[:HEADER_SIZE]
#                     )
#                     jpg_bytes = packet[HEADER_SIZE:]

#                     if len(jpg_bytes) != payload_len:
#                         continue

#                     decoder = self._decoders.get(cam_id)
#                     if decoder:
#                         decoder.enqueue(jpg_bytes)

#     def stop(self):
#         self._running = False


# class CameraReceiver(QObject):
#     frame_received = pyqtSignal(int, object)

#     SOCKET_RCVBUF = 2 * 1024 * 1024

#     def __init__(self, ports=None):
#         super().__init__()
#         self.ports = ports or [5005, 5006, 5007]
#         self.sockets: list[socket.socket] = []

#         self._decoders: dict[int, _PerCamDecoder] = {}
#         for i, port in enumerate(self.ports):
#             cam_id = i + 1
#             decoder = _PerCamDecoder(cam_id, self._on_frame_ready)
#             decoder.start()
#             self._decoders[cam_id] = decoder

#             sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#             sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
#             sock.setsockopt(socket.SOL_SOCKET,
#                             socket.SO_RCVBUF, self.SOCKET_RCVBUF)
#             sock.bind(("0.0.0.0", port))
#             sock.setblocking(False)
#             self.sockets.append(sock)
#             print(f"[CamReceiver] Listening on UDP port {port} (cam {cam_id})")

#         # Single background thread owns all socket I/O — Qt main thread
#         # no longer touches sockets at all.
#         self._poll_thread = _SocketPollThread(
#             self.sockets, self.ports, self._decoders
#         )
#         self._poll_thread.start()
#         print("[CamReceiver] Background socket poll thread + decode threads started")

#     def _on_frame_ready(self, cam_id: int, frame_rgb):
#         # Called from decode threads — queued signal emission is thread-safe.
#         self.frame_received.emit(cam_id, frame_rgb)

#     # poll() is now a no-op kept for backward compatibility with MainWindow's
#     # QTimer. You can remove the QTimer entirely, or leave it — it does nothing.
#     def poll(self):
#         pass

#     def stop(self):
#         self._poll_thread.stop()
#         self._poll_thread.join(timeout=1.0)
#         for decoder in self._decoders.values():
#             decoder.stop()
#         for sock in self.sockets:
#             try:
#                 sock.close()
#             except Exception:
#                 pass
#         print("[CamReceiver] Closed")

#     def close(self):
#         self.stop()


# #-------#

import socket
import struct
import select
import cv2
import numpy as np
import threading
import queue
import time

from PyQt6.QtCore import QObject, pyqtSignal

HEADER_FMT = ">BI"
HEADER_SIZE = struct.calcsize(HEADER_FMT)


class _PerCamDecoder(threading.Thread):
    """One decode thread per camera — frames never mix between cameras."""

    MIN_INTERVAL = 1 / 25  # cap at 25 fps per camera

    def __init__(self, cam_id: int, on_frame):
        super().__init__(daemon=True, name=f"DecodeThread-cam{cam_id}")
        self.cam_id = cam_id
        self._on_frame = on_frame
        self._queue: queue.Queue = queue.Queue(maxsize=2)
        self._running = True

    def enqueue(self, jpg_bytes: bytes):
        try:
            self._queue.put_nowait(jpg_bytes)
        except queue.Full:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                pass
            try:
                self._queue.put_nowait(jpg_bytes)
            except queue.Full:
                pass

    def run(self):
        self._last_emit = 0.0
        while self._running:
            try:
                jpg_bytes = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue

            if len(jpg_bytes) < 100:
                continue

            try:
                nparr = np.frombuffer(jpg_bytes, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if frame is not None:
                    now = time.monotonic()
                    if now - self._last_emit < self.MIN_INTERVAL:
                        continue  # drop frame, too soon
                    self._last_emit = now
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    self._on_frame(self.cam_id, frame_rgb)
            except Exception as e:
                print(f"[CamReceiver] Decode error cam {self.cam_id}: {e}")

    def stop(self):
        self._running = False


class _SocketPollThread(threading.Thread):
    """
    Dedicated background thread that drains all UDP sockets using select().
    Keeps blocking I/O entirely off the Qt main thread, eliminating the
    primary source of lag and freeze.
    """

    def __init__(self, sockets: list, ports: list, decoders: dict):
        super().__init__(daemon=True, name="SocketPollThread")
        self._sockets = sockets
        self._ports = ports
        self._decoders = decoders
        self._running = True

    def run(self):
        while self._running:
            try:
                readable, _, _ = select.select(self._sockets, [], [], 0.05)
            except Exception as e:
                print(f"[CamReceiver] select error: {e}")
                time.sleep(0.05)
                continue

            for sock in readable:
                for _ in range(5):
                    try:
                        packet, _ = sock.recvfrom(65536)
                    except BlockingIOError:
                        break
                    except OSError:
                        break
                    except Exception as e:
                        print(f"[CamReceiver] recv error: {e}")
                        break

                    if len(packet) < HEADER_SIZE:
                        continue

                    cam_id, payload_len = struct.unpack(
                        HEADER_FMT, packet[:HEADER_SIZE]
                    )
                    jpg_bytes = packet[HEADER_SIZE:]

                    if len(jpg_bytes) != payload_len:
                        continue

                    decoder = self._decoders.get(cam_id)
                    if decoder:
                        decoder.enqueue(jpg_bytes)

    def stop(self):
        self._running = False


class CameraReceiver(QObject):
    frame_received = pyqtSignal(int, object)

    SOCKET_RCVBUF = 2 * 1024 * 1024

    def __init__(self, ports=None):
        super().__init__()
        self.ports = ports or [5005, 5006, 5007]
        self.sockets: list[socket.socket] = []

        self._decoders: dict[int, _PerCamDecoder] = {}
        for i, port in enumerate(self.ports):
            cam_id = i + 1
            decoder = _PerCamDecoder(cam_id, self._on_frame_ready)
            decoder.start()
            self._decoders[cam_id] = decoder

            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.SOL_SOCKET,
                            socket.SO_RCVBUF, self.SOCKET_RCVBUF)
            sock.bind(("0.0.0.0", port))
            sock.setblocking(False)
            self.sockets.append(sock)
            print(f"[CamReceiver] Listening on UDP port {port} (cam {cam_id})")

        self._poll_thread = _SocketPollThread(
            self.sockets, self.ports, self._decoders
        )
        self._poll_thread.start()
        print("[CamReceiver] Background socket poll thread + decode threads started")

    def _on_frame_ready(self, cam_id: int, frame_rgb):
        self.frame_received.emit(cam_id, frame_rgb)

    def poll(self):
        pass  # no-op — kept for MainWindow QTimer compatibility

    def stop(self):
        self._poll_thread.stop()
        self._poll_thread.join(timeout=1.0)
        for decoder in self._decoders.values():
            decoder.stop()
        for sock in self.sockets:
            try:
                sock.close()
            except Exception:
                pass
        print("[CamReceiver] Closed")

    def close(self):
        self.stop()
