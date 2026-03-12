import socket
import struct
import cv2
import numpy as np
import threading
import queue

from PyQt6.QtCore import QObject, pyqtSignal

HEADER_FMT = ">BI"
HEADER_SIZE = struct.calcsize(HEADER_FMT)


class _PerCamDecoder(threading.Thread):
    """One decode thread per camera — frames never mix between cameras.
    Resize is done HERE, off the main thread, to prevent UI freezing.
    """

    def __init__(self, cam_id: int, on_frame):
        super().__init__(daemon=True, name=f"DecodeThread-cam{cam_id}")
        self.cam_id = cam_id
        self._on_frame = on_frame          # callable(cam_id, frame_rgb)
        # Queue holds (jpg_bytes, target_size_or_None)
        self._queue: queue.Queue = queue.Queue(maxsize=2)
        self._running = True
        # (width, height) set by main window
        self.target_size: tuple | None = None

    def enqueue(self, jpg_bytes: bytes):
        item = (jpg_bytes, self.target_size)
        try:
            self._queue.put_nowait(item)
        except queue.Full:
            # drop oldest, push newest
            try:
                self._queue.get_nowait()
            except queue.Empty:
                pass
            try:
                self._queue.put_nowait(item)
            except queue.Full:
                pass

    def run(self):
        while self._running:
            try:
                jpg_bytes, target_size = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue

            if len(jpg_bytes) < 100:
                continue

            try:
                nparr = np.frombuffer(jpg_bytes, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if frame is None:
                    continue

                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                # ── Resize here, NOT on the main thread ──────────────────
                if target_size:
                    tw, th = target_size
                    fh, fw = frame_rgb.shape[:2]
                    if fw > 0 and fh > 0 and (fw != tw or fh != th):
                        scale = min(tw / fw, th / fh)
                        nw = max(1, int(fw * scale))
                        nh = max(1, int(fh * scale))
                        frame_rgb = cv2.resize(
                            frame_rgb, (nw, nh),
                            interpolation=cv2.INTER_LINEAR
                        )

                self._on_frame(self.cam_id, frame_rgb)

            except Exception as e:
                print(f"[CamReceiver] Decode error cam {self.cam_id}: {e}")

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

        print("[CamReceiver] Per-camera decode threads started")

    def set_label_size(self, cam_id: int, width: int, height: int):
        """Call this from the main window when label size changes (e.g. fullscreen)."""
        decoder = self._decoders.get(cam_id)
        if decoder and width > 0 and height > 0:
            decoder.target_size = (width, height)

    def _on_frame_ready(self, cam_id: int, frame_rgb):
        self.frame_received.emit(cam_id, frame_rgb)

    def poll(self):
        """Drain sockets — called from QTimer on main thread."""
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
                    HEADER_FMT, packet[:HEADER_SIZE])
                jpg_bytes = packet[HEADER_SIZE:]

                if len(jpg_bytes) != payload_len:
                    continue

                decoder = self._decoders.get(cam_id)
                if decoder:
                    decoder.enqueue(jpg_bytes)

    def stop(self):
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
