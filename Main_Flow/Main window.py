"""
Key bindings:
  C  → start recording camera 1
  S  → stop  recording

Fixes applied vs original:
  1. cv2.resize() moved OFF main thread (into decode threads via set_label_size)
  2. resizeEvent() updates decoder target sizes so fullscreen never freezes
  3. SensorWebSocketThread uses port 9000 (not 8888) — no port conflict with control
  4. Control commands use correct "c <pwm>,..." format (space not comma)
  5. CameraRecorder stop_recording no longer deadlocks
"""

import sys
import os
import cv2
import PyQt6

from PyQt6.QtWidgets import QApplication, QMainWindow, QSizePolicy
from PyQt6 import uic
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QImage, QPixmap

from Cam_Reciever import CameraReceiver
from Sensor_Client import SensorClient
from Cam_Recorder import CameraRecorder
from Control_Thread import ControlThread
from Sensor_Websocket_Thread import SensorWebSocketThread

_plugin_path = os.path.join(
    os.path.dirname(PyQt6.__file__), "Qt6", "plugins", "platforms"
)
os.environ.setdefault("QT_QPA_PLATFORM_PLUGIN_PATH", _plugin_path)

UI_FILE = "/Users/kashishkapoor/Ranger-25-26/Main_Flow/Mate_ROV.ui"


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        uic.loadUi(UI_FILE, self)

        self._setup_cameras()
        self._setup_sensors()
        self._setup_control()

        print("\n" + "=" * 52)
        print("  ROV CONTROL SYSTEM READY")
        print("  Cameras : 3 feeds on ports 5005-5007")
        print("  Record  : C = start  |  S = stop")
        print("  Sensors : UDP port 9000 → WebSocket 8765")
        print("  Control : joystick @ 20 Hz → Arduino port 8888")
        print("=" * 52 + "\n")

    # ── Setup ─────────────────────────────────────────────────────────────

    def _setup_cameras(self):
        for label in [self.Camera_Feed_1, self.Camera_Feed_2, self.Camera_Feed_3]:
            label.setScaledContents(False)
            label.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
            label.setMinimumSize(320, 240)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("background-color: black;")

        self.camera_receiver = CameraReceiver(ports=[5005, 5006, 5007])
        self.camera_receiver.frame_received.connect(self.update_camera)

        self.cam_timer = QTimer(self)
        self.cam_timer.timeout.connect(self.camera_receiver.poll)
        self.cam_timer.start(16)  # ~60 Hz poll

        self.recorder = CameraRecorder(frame_size=(320, 240))

        # Push initial label sizes to decoders after window is shown
        QTimer.singleShot(200, self._push_label_sizes)

    def _setup_sensors(self):
        # ── FIX: sensor UDP on port 9000, NOT 8888 ───────────────────────
        # 8888 is used exclusively by ControlThread for thruster commands.
        # Update your Arduino sketch to send HUM:/CUR: packets to port 9000.
        self.sensor_ws_thread = SensorWebSocketThread(
            ws_port=8765, udp_port=9000)
        self.sensor_ws_thread.start()

        self.sensor_client = SensorClient(ws_url="ws://localhost:8765")
        self.sensor_client.data_received.connect(self.update_sensors)
        QTimer.singleShot(1000, self.sensor_client.start)

    def _setup_control(self):
        self.control_thread = ControlThread(
            arduino_ip="192.168.1.151", arduino_port=8888
        )
        self.control_timer = QTimer(self)
        self.control_timer.timeout.connect(self.control_thread.process_events)
        self.control_timer.start(50)  # 20 Hz

    # ── Label size sync ───────────────────────────────────────────────────

    def _push_label_sizes(self):
        """Tell each decoder the current label size so it can resize frames."""
        label_map = {
            1: self.Camera_Feed_1,
            2: self.Camera_Feed_2,
            3: self.Camera_Feed_3,
        }
        for cam_id, label in label_map.items():
            self.camera_receiver.set_label_size(
                cam_id, label.width(), label.height())

    def resizeEvent(self, event):
        """Called on window resize AND fullscreen — update decoder targets."""
        super().resizeEvent(event)
        self._push_label_sizes()

    # ── Slots ─────────────────────────────────────────────────────────────

    def update_camera(self, cam_id: int, frame_rgb):
        """
        Frames arrive already resized from the decode thread.
        Main thread only does: numpy → QImage → QPixmap. No cv2 work here.
        """
        label_map = {
            1: self.Camera_Feed_1,
            2: self.Camera_Feed_2,
            3: self.Camera_Feed_3,
        }
        label = label_map.get(cam_id)
        if label is None:
            return

        h, w, ch = frame_rgb.shape
        qimg = QImage(frame_rgb.data, w, h, ch * w,
                      QImage.Format.Format_RGB888)
        label.setPixmap(QPixmap.fromImage(qimg.copy()))

        if cam_id == 1 and self.recorder.recording:
            self.recorder.write_frame(
                cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
            )

    def update_sensors(self, data: dict):
        humidity = data.get("humidity", 0)
        current = data.get("current",  0)
        self.Humidity_Data.setText(f"Humidity: {humidity} %")
        self.Current_Data.setText(f"Current: {current} A")

    # ── Key bindings ──────────────────────────────────────────────────────

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key.Key_C:
            self.recorder.start_recording()
        elif key == Qt.Key.Key_S:
            self.recorder.stop_recording()

    # ── Shutdown ──────────────────────────────────────────────────────────

    def closeEvent(self, event):
        print("\n[Main] Shutting down…")
        for attr in ("control_timer", "cam_timer"):
            timer = getattr(self, attr, None)
            if timer:
                timer.stop()
        for attr in ("control_thread", "sensor_ws_thread",
                     "camera_receiver", "sensor_client"):
            obj = getattr(self, attr, None)
            if obj:
                obj.stop()
        rec = getattr(self, "recorder", None)
        if rec:
            rec.stop_recording()
        print("[Main] Shutdown complete")
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
