import socket
import threading
import time


class BoostController:

    CONTROL_PORT = 5010
    BOOST_DURATION = 5.0

    def __init__(self, pi_ip: str = "192.168.1.151"):
        self.pi_ip = pi_ip
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._boost_active = {}

    def boost(self, cam_id: int):
        if self._boost_active.get(cam_id):
            self._send(f"boost:{cam_id}")
            return

        self._boost_active[cam_id] = True
        self._send(f"boost:{cam_id}")
        threading.Timer(
            self.BOOST_DURATION,
            self._clear_boost, args=(cam_id,)
        ).start()

    def drop(self, cam_id: int):
        self._boost_active[cam_id] = False
        self._send(f"drop:{cam_id}")

    def is_boosted(self, cam_id: int) -> bool:
        return bool(self._boost_active.get(cam_id))

    def close(self):
        self._sock.close()

    def _send(self, msg: str):
        try:
            self._sock.sendto(msg.encode(), (self.pi_ip, self.CONTROL_PORT))
        except Exception as e:
            print(f"[BoostCtrl] Send error: {e}")

    def _clear_boost(self, cam_id: int):
        self._boost_active[cam_id] = False
