import socket
import struct
import cv2
import numpy as np
import threading
import time

from PyQt6.QtCore import QObject, pyqtSignal, Qt

HEADER_FMT = ">BI"
HEADER_SIZE = struct.calcsize(HEADER_FMT)
MAX_QUEUE_DEPTH = 2


class FrameDecodeWorker(QObject):
    frame_ready = pyqtSignal(int, object)

    def __init__(self):
        super().__init__()
        self._queue: list[tuple[int, bytes]] = []
        self._lock = threading.Lock()
        self._running = True

    def enqueue(self, cam_id: int, jpg_bytes: bytes):
        with self._lock:
            self._queue = [x for x in self._queue if x[0] != cam_id]
            self._queue.append((cam_id, jpg_bytes))

    def run(self):
        while self._running:
            item = None
            with self._lock:
                if self._queue:
                    item = self._queue.pop(0)

            if item is None:
                time.sleep(0.001)
                continue

            cam_id, jpg_bytes = item
            if len(jpg_bytes) < 100:
                continue

            try:
                nparr = np.frombuffer(jpg_bytes, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if frame is not None:
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    self.frame_ready.emit(cam_id, frame_rgb)
            except Exception as e:
                print(f"[CamReceiver] Decode error cam {cam_id}: {e}")

    def stop(self):
        self._running = False


class CameraReceiver(QObject):
    frame_received = pyqtSignal(int, object)

    SOCKET_RCVBUF = 2 * 1024 * 1024
    READ_SIZE = 65536

    def __init__(self, ports=None):
        super().__init__()
        self.ports = ports or [5005, 5006, 5007]
        self.sockets: list[socket.socket] = []

        for port in self.ports:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.SOL_SOCKET,
                            socket.SO_RCVBUF, self.SOCKET_RCVBUF)
            sock.bind(("0.0.0.0", port))
            sock.setblocking(False)
            self.sockets.append(sock)
            print(f"[CamReceiver] Listening on UDP port {port}")

        self._worker = FrameDecodeWorker()
        self._worker.frame_ready.connect(
            self.frame_received,
            Qt.ConnectionType.QueuedConnection
        )

        self._thread = threading.Thread(
            target=self._worker.run, daemon=True, name="FrameDecodeThread"
        )
        self._thread.start()
        print("[CamReceiver] Decode thread started")

    def poll(self):
        for i, sock in enumerate(self.sockets):
            for _ in range(20):
                try:
                    packet, _ = sock.recvfrom(self.READ_SIZE)
                except BlockingIOError:
                    break
                except OSError:
                    break
                except Exception as e:
                    print(
                        f"[CamReceiver] Socket error port {self.ports[i]}: {e}")
                    break

                if len(packet) < HEADER_SIZE:
                    continue

                cam_id, payload_len = struct.unpack(
                    HEADER_FMT, packet[:HEADER_SIZE]
                )
                jpg_bytes = packet[HEADER_SIZE:]

                if len(jpg_bytes) != payload_len:
                    continue

                self._worker.enqueue(cam_id, jpg_bytes)

    def close(self):
        self._worker.stop()
        self._thread.join(timeout=2.0)
        for sock in self.sockets:
            try:
                sock.close()
            except Exception:
                pass
        print("[CamReceiver] Closed")
