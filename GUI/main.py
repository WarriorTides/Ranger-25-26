import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QSizePolicy
from PyQt6 import uic
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QImage, QPixmap
from CamReceiver_Dummy import CameraReceiver
from SensorClient_Dummy import SensorClient
from Cam_Recorder import CameraRecorder
import cv2
import os
import PyQt6

plugin_path = os.path.join(os.path.dirname(
    PyQt6.__file__), "Qt6", "plugins", "platforms")
os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = plugin_path


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("/Users/kashishkapoor/Desktop/Mate_ROV.ui", self)

        for label in [self.Camera_Feed_1, self.Camera_Feed_2, self.Camera_Feed_3]:
            label.setScaledContents(True)
            label.setSizePolicy(QSizePolicy.Policy.Expanding,
                                QSizePolicy.Policy.Expanding)
            label.setMinimumSize(320, 240)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("background-color: black;")

        self.camera_receiver = CameraReceiver()
        self.camera_receiver.frame_received.connect(self.update_camera)
        self.timer = QTimer()
        self.timer.timeout.connect(self.camera_receiver.poll)
        self.timer.start(10)

        self.recorder = CameraRecorder(frame_size=(640, 480))

        self.sensor_client = SensorClient()
        self.sensor_client.data_received.connect(self.update_sensors)
        self.sensor_client.start()

    def update_camera(self, cam_id, frame):
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame_rgb.shape
        qimg = QImage(frame_rgb.data, w, h, ch * w,
                      QImage.Format.Format_RGB888)
        pix = QPixmap.fromImage(qimg)

        label_map = {
            1: self.Camera_Feed_1,
            2: self.Camera_Feed_2,
            3: self.Camera_Feed_3
        }

        label = label_map.get(cam_id)
        if label:
            label.setPixmap(pix)

        if cam_id == 1:
            self.recorder.write_frame(frame)

    def update_sensors(self, data):
        self.Humidity_Data.setText(f"Humidity: {data.get('humidity', 0)} %")

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key.Key_C:
            self.recorder.start_recording()
        elif key == Qt.Key.Key_S:
            self.recorder.stop_recording()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
