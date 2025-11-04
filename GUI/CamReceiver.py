import socket
import json
import base64
import cv2
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal


class CameraReceiver(QObject):
    frame_received = pyqtSignal(int, object)

    def __init__(self, ports=[5005, 5006, 5007]):
        super().__init__()
        self.ports = ports
        self.sockets = []
        for port in ports:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind(("0.0.0.0", port))
            sock.setblocking(False)
            self.sockets.append(sock)

    def poll(self):
        for idx, sock in enumerate(self.sockets):
            try:
                while True:
                    data, addr = sock.recvfrom(65536)
                    msg = json.loads(data.decode())
                    if msg['type'] == 'camera':
                        cam_id = int(msg['camera_id'])
                        jpg_bytes = base64.b64decode(msg['data'])
                        nparr = np.frombuffer(jpg_bytes, np.uint8)
                        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                        if frame is not None:
                            self.frame_received.emit(cam_id, frame)
            except BlockingIOError:
                continue
            except Exception as e:
                print(f"CameraReceiver error: {e}")
