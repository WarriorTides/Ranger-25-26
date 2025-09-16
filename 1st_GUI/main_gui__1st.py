import PyQt6
from PyQt6 import uic
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtCore import QThread, Qt
from PyQt6.QtGui import QImage, QPixmap
import cv2
import sys
from Cam_Threads import CameraThread
from Claw_Threads import ClawThread
from Sensor_Threads import SensorThread
from PyQt6.QtWidgets import QSizePolicy
import os

plugin_path = os.path.join(os.path.dirname(PyQt6.__file__), 'Qt6', 'plugins', 'platforms')
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = plugin_path

import websocket
import threading
import json
import time


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        uic.loadUi("/Users/kashishkapoor/Desktop/Mate_ROV.ui", self)
        self.aspect_ratio = 16.0 / 9.0
        self.showMaximized()

        if self.centralWidget():
            size_policy = self.centralWidget().sizePolicy()
            size_policy.setHorizontalPolicy(QSizePolicy.Policy.Expanding)
            size_policy.setVerticalPolicy(QSizePolicy.Policy.Expanding)
            self.centralWidget().setSizePolicy(size_policy)

        self.setup_camera_feeds()

    def setup_camera_feeds(self):
        """Configure camera feed labels with proper sizing constraints"""
        max_width = 640
        max_height = 480
        
        if hasattr(self, 'Camera_Feed_1'):
            self.Camera_Feed_1.setMaximumSize(max_width, max_height)
            self.Camera_Feed_1.setMinimumSize(320, 240)
            self.Camera_Feed_1.setScaledContents(False)
            self.Camera_Feed_1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        if hasattr(self, 'Camera_Feed_2'):
            self.Camera_Feed_2.setMaximumSize(max_width, max_height)
            self.Camera_Feed_2.setMinimumSize(320, 240)
            self.Camera_Feed_2.setScaledContents(False)
            self.Camera_Feed_2.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
        if hasattr(self, 'Camera_Feed_3'):
            self.Camera_Feed_3.setMaximumSize(max_width, max_height)
            self.Camera_Feed_3.setMinimumSize(320, 240)
            self.Camera_Feed_3.setScaledContents(False)
            self.Camera_Feed_3.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def closeEvent(self, event):
        camera1.stop()
        camera2.stop()
        camera3.stop()  
        claw1_thread.stop()
        claw2_thread.stop()
        sensor_thread.stop()
        if ws_connected:
            ws_app.close()
        event.accept()


def update_camera1(frame):
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    h, w, ch = frame.shape
    bytes_per_line = ch * w
    qimg = QImage(frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
    pixmap = QPixmap.fromImage(qimg)
    max_size = window.Camera_Feed_1.maximumSize()
    scaled_pixmap = pixmap.scaled(max_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    window.Camera_Feed_1.setPixmap(scaled_pixmap)

def update_camera2(frame):
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    h, w, ch = frame.shape
    bytes_per_line = ch * w
    qimg = QImage(frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
    pixmap = QPixmap.fromImage(qimg)
    max_size = window.Camera_Feed_2.maximumSize()
    scaled_pixmap = pixmap.scaled(max_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    window.Camera_Feed_2.setPixmap(scaled_pixmap)

def update_camera3(frame):
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    h, w, ch = frame.shape
    bytes_per_line = ch * w
    qimg = QImage(frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
    pixmap = QPixmap.fromImage(qimg)
    max_size = window.Camera_Feed_3.maximumSize()
    scaled_pixmap = pixmap.scaled(max_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    window.Camera_Feed_3.setPixmap(scaled_pixmap)

def update_claw1_status(status):
    window.Claw_One_Status.setText(f"Claw Status One: {status}")
    if ws_connected:
        ws_app.send(json.dumps({"claw": "Claw 1", "status": status}))

def update_claw2_status(status):
    window.Claw_Two_Status.setText(f"Claw Status Two: {status}")
    if ws_connected:
        ws_app.send(json.dumps({"claw": "Claw 2", "status": status}))

def update_sensor_data(data):
    window.Humidity_Data.setText(f"Humidity: {data['humidity']}%")
    window.Depth_Data.setText(f"Depth: {data['depth']} m")
    window.Temp_Data.setText(f"Temperature: {data['temperature']}°C")
    window.Leak_data.setText(f"Leak: {data['leak']}%")
    
    if ws_connected:
        ws_app.send(json.dumps({"sensor": data}))

def on_message(ws, message):
    print("Received from server:", message)

def on_open(ws):
    global ws_connected
    print("Connected to server!")
    ws_connected = True

def on_close(ws, close_status_code, close_msg):
    global ws_connected
    print("WebSocket closed")
    ws_connected = False


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    ws_connected = False
    ws_app = websocket.WebSocketApp(
        "ws://localhost:8080",
        on_message=on_message,
        on_open=on_open,
        on_close=on_close
    )
    threading.Thread(target=ws_app.run_forever, daemon=True).start()

    camera1 = CameraThread(0)  
    camera2 = CameraThread(1)  
    camera3 = CameraThread(2) 
    
    camera1.frame_updated.connect(update_camera1)
    camera2.frame_updated.connect(update_camera2)
    camera3.frame_updated.connect(update_camera3)  
    
    camera1.start()
    camera2.start()
    camera3.start()  
    
    claw1_thread = ClawThread("Claw 1")
    claw2_thread = ClawThread("Claw 2")
    claw1_thread.status_updated.connect(update_claw1_status)
    claw2_thread.status_updated.connect(update_claw2_status)
    claw1_thread.start()
    claw2_thread.start()
    sensor_thread = SensorThread()
    sensor_thread.data_updated.connect(update_sensor_data)
    sensor_thread.start()
    window.show()
    sys.exit(app.exec())