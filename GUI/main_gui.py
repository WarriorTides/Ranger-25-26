from PyQt6 import uic
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtCore import QThread
from PyQt6.QtGui import QImage, QPixmap
import cv2
import sys
from GUI.Cam_Threads import CameraThread
from GUI.Claw_Threads import ClawThread
from GUI.Sensor_Threads import SensorThread 

def update_camera1(frame):
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    h, w, ch = frame.shape
    bytes_per_line = ch * w
    qimg = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
    window.Camera_Feed_1.setPixmap(QPixmap.fromImage(qimg))

def update_camera2(frame):
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    h, w, ch = frame.shape
    bytes_per_line = ch * w
    qimg = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
    window.Camera_Feed_2.setPixmap(QPixmap.fromImage(qimg))

def update_camera3(frame):
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    h, w, ch = frame.shape
    bytes_per_line = ch * w
    qimg = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
    window.Camera_Feed_3.setPixmap(QPixmap.fromImage(qimg))

def update_claw1_status(status):
    window.Claw_One_Status.setText(f"Claw Status One: {status}")

def update_claw2_status(status):
    window.Claw_Two_Status.setText(f"Claw Status Two: {status}")

def update_sensor_data(data):
    window.Humidity_Label.setText(f"Humidity: {data['humidity']}%")
    window.Depth_Label.setText(f"Depth: {data['depth']} m")
    window.Temp_Label.setText(f"Temperature: {data['temperature']}°C")
    window.Leak_Label.setText(f"Leak: {data['leak']}%")

app = QApplication(sys.argv) 
window = QMainWindow()        
uic.loadUi("Mate_ROV.ui", window)  

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

def closeEvent(event):
    camera1.stop()
    camera2.stop()
    camera3.stop()
    claw1_thread.stop()
    claw2_thread.stop()
    sensor_thread.stop()   
    event.accept()

window.closeEvent = closeEvent
sys.exit(app.exec())  
