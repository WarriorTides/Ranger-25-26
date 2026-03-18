# """
# Key bindings:
#   C  → start recording camera 1
#   S  → stop  recording
# """

# import sys
# import os
# import cv2
# import PyQt6

# from PyQt6.QtWidgets import QApplication, QMainWindow, QSizePolicy
# from PyQt6 import uic
# from PyQt6.QtCore import QTimer, Qt, QSize
# from PyQt6.QtGui import QImage, QPixmap

# from Camreceiver import CameraReceiver
# from Sensor_Client import SensorClient
# from Cam_Recorder import CameraRecorder
# from Control_Thread import ControlThread
# from Sensor_Websocket_Thread import SensorWebSocketThread

# _plugin_path = os.path.join(
#     os.path.dirname(PyQt6.__file__), "Qt6", "plugins", "platforms"
# )
# os.environ.setdefault("QT_QPA_PLATFORM_PLUGIN_PATH", _plugin_path)

# UI_FILE = "/Users/kashishkapoor/Ranger-25-26/Main_Flow/Mate_ROV.ui"

# # Cache label sizes after the window is shown to avoid reading
# # unstable geometry during layout passes.
# _LABEL_SIZE_CACHE: dict[int, QSize] = {}


# class MainWindow(QMainWindow):

#     def __init__(self):
#         super().__init__()
#         uic.loadUi(UI_FILE, self)

#         self._setup_cameras()
#         self._setup_sensors()
#         self._setup_control()

#         print("\n" + "=" * 52)
#         print("  ROV CONTROL SYSTEM READY")
#         print("  Cameras : 3 feeds on ports 5005-5007")
#         print("  Record  : C = start  |  S = stop")
#         print("  Sensors : auto-reconnect WebSocket")
#         print("  Control : joystick @ 20 Hz")
#         print("=" * 52 + "\n")

#     def _setup_cameras(self):
#         for label in [self.Camera_Feed_1, self.Camera_Feed_2, self.Camera_Feed_3]:
#             # Never let the label scale its own contents — we do it manually
#             label.setScaledContents(False)
#             # Expanding but with a hard minimum so layout doesn't collapse it
#             label.setSizePolicy(
#                 QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
#             )
#             label.setMinimumSize(320, 240)
#             label.setAlignment(Qt.AlignmentFlag.AlignCenter)
#             label.setStyleSheet("background-color: black;")

#         self.camera_receiver = CameraReceiver(ports=[5005, 5006, 5007])
#         self.camera_receiver.frame_received.connect(self.update_camera)
#         self.cam_timer = QTimer(self)
#         self.cam_timer.timeout.connect(self.camera_receiver.poll)
#         self.cam_timer.start(16)

#         self.recorder = CameraRecorder(frame_size=(320, 240))

#         # Invalidate the label-size cache whenever the window is resized so
#         # the next frame recalculates the scaled pixmap at the correct size.
#         self._resize_pending = False

#     def _label_for(self, cam_id: int):
#         return {
#             1: self.Camera_Feed_1,
#             2: self.Camera_Feed_2,
#             3: self.Camera_Feed_3,
#         }.get(cam_id)

#     def _setup_sensors(self):
#         self.sensor_ws_thread = SensorWebSocketThread(
#             ws_port=8765, udp_port=8888)
#         self.sensor_ws_thread.start()

#         self.sensor_client = SensorClient(ws_url="ws://localhost:8765")
#         self.sensor_client.data_received.connect(self.update_sensors)
#         QTimer.singleShot(1000, self.sensor_client.start)

#     def _setup_control(self):
#         self.control_thread = ControlThread(
#             arduino_ip="192.168.1.151", arduino_port=8888
#         )
#         self.control_timer = QTimer(self)
#         self.control_timer.timeout.connect(self.control_thread.process_events)
#         self.control_timer.start(50)

#     # ------------------------------------------------------------------
#     # Resize event — clear the size cache so the next frame re-scales
#     # correctly.  We use a short debounce timer so we don't thrash while
#     # the user is still dragging the window border.
#     # ------------------------------------------------------------------
#     def resizeEvent(self, event):
#         super().resizeEvent(event)
#         if not self._resize_pending:
#             self._resize_pending = True
#             QTimer.singleShot(150, self._on_resize_settled)

#     def _on_resize_settled(self):
#         _LABEL_SIZE_CACHE.clear()
#         self._resize_pending = False

#     # ------------------------------------------------------------------
#     # Camera frame handler
#     # ------------------------------------------------------------------
#     def update_camera(self, cam_id: int, frame_rgb):
#         label = self._label_for(cam_id)
#         if label is None:
#             return

#         # Use cached label size; only re-read from the widget when the
#         # cache is empty (startup or after a resize settled).
#         if cam_id not in _LABEL_SIZE_CACHE:
#             lw, lh = label.width(), label.height()
#             if lw < 1 or lh < 1:
#                 # Widget not laid out yet — skip this frame
#                 return
#             _LABEL_SIZE_CACHE[cam_id] = QSize(lw, lh)

#         cached = _LABEL_SIZE_CACHE[cam_id]
#         lw, lh = cached.width(), cached.height()

#         fh, fw = frame_rgb.shape[:2]

#         # Letterbox-scale the frame to fit the label exactly once per
#         # stable label size, avoiding per-frame geometry reads.
#         scale = min(lw / fw, lh / fh)
#         new_w = max(1, int(fw * scale))
#         new_h = max(1, int(fh * scale))

#         if new_w != fw or new_h != fh:
#             frame_rgb = cv2.resize(
#                 frame_rgb, (new_w, new_h), interpolation=cv2.INTER_LINEAR
#             )

#         h, w, ch = frame_rgb.shape
#         bytes_per_line = ch * w
#         qimg = QImage(frame_rgb.data, w, h, bytes_per_line,
#                       QImage.Format.Format_RGB888)
#         # .copy() detaches the QImage from the numpy buffer before the
#         # buffer might be freed by the next poll cycle.
#         label.setPixmap(QPixmap.fromImage(qimg.copy()))

#         if cam_id == 1 and self.recorder.recording:
#             self.recorder.write_frame(
#                 cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
#             )

#     def update_sensors(self, data: dict):
#         humidity = data.get("humidity", 0)
#         current = data.get("current",  0)
#         self.Humidity_Data.setText(f"Humidity: {humidity} %")
#         self.Current_Data.setText(f"Current: {current} A")

#     def keyPressEvent(self, event):
#         key = event.key()
#         if key == Qt.Key.Key_C:
#             self.recorder.start_recording()
#         elif key == Qt.Key.Key_S:
#             self.recorder.stop_recording()

#     def closeEvent(self, event):
#         print("\n[Main] Shutting down…")
#         for attr in ("control_timer", "cam_timer"):
#             timer = getattr(self, attr, None)
#             if timer:
#                 timer.stop()
#         for attr in ("control_thread", "sensor_ws_thread",
#                      "camera_receiver", "sensor_client"):
#             obj = getattr(self, attr, None)
#             if obj:
#                 obj.stop()
#         rec = getattr(self, "recorder", None)
#         if rec:
#             rec.stop_recording()
#         print("[Main] Shutdown complete")
#         event.accept()


# if __name__ == "__main__":
#     app = QApplication(sys.argv)
#     window = MainWindow()
#     window.show()
#     sys.exit(app.exec())


"""
Key bindings:
  C  → start recording camera 1
  S  → stop  recording
"""

import sys
import os
import cv2
import PyQt6

from PyQt6.QtWidgets import QApplication, QMainWindow, QSizePolicy
from PyQt6 import uic
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QImage, QPixmap

from Camreceiver import CameraReceiver
from Sensor_Client import SensorClient
from Cam_Recorder import CameraRecorder
from Control_Thread import ControlThread
from Sensor_Websocket_Thread import SensorWebSocketThread

_plugin_path = os.path.join(
    os.path.dirname(PyQt6.__file__), "Qt6", "plugins", "platforms"
)
os.environ.setdefault("QT_QPA_PLATFORM_PLUGIN_PATH", _plugin_path)

UI_FILE = "/Users/kashishkapoor/Ranger-25-26/Main_Flow/Mate_ROV.ui"

# CamReceiver will resize frames to this size on its decode threads,
# so update_camera almost never needs to call cv2.resize.
DISPLAY_SIZE = (320, 240)


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        uic.loadUi(UI_FILE, self)

        # FIX #6 — keep a reference to the latest numpy frame per camera so
        # the QImage's backing buffer stays alive until the next frame arrives.
        # Without this the buffer is freed by Python GC while Qt still holds a
        # pointer to it, causing corruption or a crash.
        self._live_frames: dict[int, object] = {}

        self._setup_cameras()
        self._setup_sensors()
        self._setup_control()

        print("\n" + "=" * 52)
        print("  ROV CONTROL SYSTEM READY")
        print("  Cameras : 3 feeds on ports 5005-5007")
        print("  Record  : C = start  |  S = stop")
        print("  Sensors : auto-reconnect WebSocket")
        print("  Control : joystick @ 20 Hz")
        print("=" * 52 + "\n")

    def _setup_cameras(self):
        for label in [self.Camera_Feed_1, self.Camera_Feed_2, self.Camera_Feed_3]:
            label.setScaledContents(False)
            label.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
            label.setMinimumSize(320, 240)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("background-color: black;")

        # Pass display_size so decode threads resize before emitting —
        # the main thread never calls cv2.resize (FIX #1 / FIX #4)
        self.camera_receiver = CameraReceiver(
            ports=[5005, 5006, 5007],
            display_size=DISPLAY_SIZE,
        )
        self.camera_receiver.frame_received.connect(self.update_camera)

        self.cam_timer = QTimer(self)
        self.cam_timer.timeout.connect(self.camera_receiver.poll)
        self.cam_timer.start(16)   # ~60 Hz poll — plenty for 15fps cameras

        self.recorder = CameraRecorder(frame_size=DISPLAY_SIZE)

    def _label_for(self, cam_id: int):
        return {
            1: self.Camera_Feed_1,
            2: self.Camera_Feed_2,
            3: self.Camera_Feed_3,
        }.get(cam_id)

    def _setup_sensors(self):
        self.sensor_ws_thread = SensorWebSocketThread(
            ws_port=8765, udp_port=8888)
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
        self.control_timer.start(50)

    # ------------------------------------------------------------------
    # Camera frame handler
    # ------------------------------------------------------------------
    def update_camera(self, cam_id: int, frame_rgb):
        """
        FIX #6 — no .copy() on the QImage.

        The decode thread already sized the frame to DISPLAY_SIZE, so
        cv2.resize is almost never needed here.  When it is (label
        unexpectedly larger), we still do it, but that's the rare path.

        We store frame_rgb in self._live_frames so Python does NOT free
        the underlying numpy buffer while the QImage still references it.
        The old code called qimg.copy() to work around this, which did a
        full CPU memcpy on every frame — eliminated here.
        """
        label = self._label_for(cam_id)
        if label is None:
            return

        lw, lh = label.width(), label.height()
        if lw < 1 or lh < 1:
            return

        fh, fw = frame_rgb.shape[:2]

        # Only resize if the label is bigger than what the decode thread
        # produced (rare — only happens if the window is unusually large).
        if fw != lw or fh != lh:
            scale = min(lw / fw, lh / fh)
            new_w = max(1, int(fw * scale))
            new_h = max(1, int(fh * scale))
            if new_w != fw or new_h != fh:
                frame_rgb = cv2.resize(
                    frame_rgb, (new_w, new_h), interpolation=cv2.INTER_LINEAR
                )

        # Keep the array alive — QImage does NOT own the buffer
        self._live_frames[cam_id] = frame_rgb

        h, w, ch = frame_rgb.shape
        qimg = QImage(
            frame_rgb.data, w, h, ch * w, QImage.Format.Format_RGB888
        )
        label.setPixmap(QPixmap.fromImage(qimg))   # no .copy() needed

        if cam_id == 1 and self.recorder.recording:
            self.recorder.write_frame(
                cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR))

    def update_sensors(self, data: dict):
        humidity = data.get("humidity", 0)
        current = data.get("current",  0)
        self.Humidity_Data.setText(f"Humidity: {humidity} %")
        self.Current_Data.setText(f"Current: {current} A")

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key.Key_C:
            self.recorder.start_recording()
        elif key == Qt.Key.Key_S:
            self.recorder.stop_recording()

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
        self._live_frames.clear()
        print("[Main] Shutdown complete")
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
