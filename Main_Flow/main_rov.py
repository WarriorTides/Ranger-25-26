import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QSizePolicy
from PyQt6 import uic
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QImage, QPixmap
from CamReceiver import CameraReceiver
from SensorClient import SensorClient
from Cam_Recorder import CameraRecorder
from control_thread import ControlThread
from sensor_websocket_thread import SensorWebSocketThread
import cv2
import os
import PyQt6

# Set up Qt plugin path
plugin_path = os.path.join(os.path.dirname(
    PyQt6.__file__), "Qt6", "plugins", "platforms")
os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = plugin_path


class MainWindow(QMainWindow):
    """
    Main ROV control interface.
    Integrates:
    - Camera feeds (3 cameras)
    - Camera recording
    - Sensor display (humidity, current)
    - Thruster control (via joystick)
    - Claw control (via joystick buttons)
    """

    def __init__(self):
        super().__init__()

        # Load UI file - CHANGE THIS PATH TO YOUR .UI FILE LOCATION
        uic.loadUi(
            "/Users/kashishkapoor/Ranger-25-26/Main_Flow/Mate_ROV.ui", self)

        # ========================================
        # Camera Feed Setup
        # ========================================
        print("Setting up camera feeds...")
        for label in [self.Camera_Feed_1, self.Camera_Feed_2, self.Camera_Feed_3]:
            label.setScaledContents(True)
            label.setSizePolicy(QSizePolicy.Policy.Expanding,
                                QSizePolicy.Policy.Expanding)
            label.setMinimumSize(320, 240)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("background-color: black;")

        # Camera receiver - receives frames via UDP
        self.camera_receiver = CameraReceiver()
        self.camera_receiver.frame_received.connect(self.update_camera)

        # Timer to poll for new camera frames
        self.timer = QTimer()
        self.timer.timeout.connect(self.camera_receiver.poll)
        self.timer.start(10)  # Poll every 10ms

        # Camera recorder - records camera 1
        self.recorder = CameraRecorder(frame_size=(320, 240))
        print("Camera feeds initialized")

        # ========================================
        # Sensor Display Setup
        # ========================================
        print("Setting up sensor client...")
        # Sensor client - connects to WebSocket server to receive sensor data
        # CHANGE THIS TO localhost SINCE SERVER RUNS IN SAME PROGRAM
        self.sensor_client = SensorClient(ws_url="ws://localhost:8765")
        self.sensor_client.data_received.connect(self.update_sensors)
        self.sensor_client.start()
        print("Sensor client started")

        # ========================================
        # Control System Setup (NEW)
        # ========================================
        print("Starting control system...")
        # Control thread - handles joystick input for thrusters and claw
        # CHANGE arduino_ip TO YOUR ARDUINO'S IP ADDRESS
        self.control_thread = ControlThread(
            arduino_ip="192.168.1.151",
            arduino_port=8888
        )
        self.control_thread.start()
        print("Control thread started")

        # ========================================
        # Sensor WebSocket Server Setup (NEW)
        # ========================================
        print("Starting sensor WebSocket server...")
        # Sensor WebSocket server - receives sensor data from Arduino
        # and forwards to sensor client above
        self.sensor_ws_thread = SensorWebSocketThread(
            ws_port=8765,
            udp_port=8888
        )
        self.sensor_ws_thread.start()
        print("Sensor WebSocket server started")

        print("\n" + "="*50)
        print("ROV CONTROL SYSTEM FULLY INITIALIZED")
        print("="*50)
        print("✓ Camera feeds ready (3 cameras)")
        print("✓ Camera recording ready (press 'C' to start, 'S' to stop)")
        print("✓ Sensor display ready")
        print("✓ Thruster control active (joystick)")
        print("✓ Claw control active (joystick buttons)")
        print("✓ Sensor WebSocket server running")
        print("="*50 + "\n")

    def update_camera(self, cam_id, frame):
        """
        Called when a new camera frame is received.
        Updates the appropriate camera feed display.
        """
        # Convert BGR to RGB for Qt display
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame_rgb.shape
        qimg = QImage(frame_rgb.data, w, h, ch * w,
                      QImage.Format.Format_RGB888)
        pix = QPixmap.fromImage(qimg)

        # Map camera ID to display label
        label_map = {
            1: self.Camera_Feed_1,
            2: self.Camera_Feed_2,
            3: self.Camera_Feed_3
        }

        label = label_map.get(cam_id)
        if label:
            label.setPixmap(pix)

        # Record camera 1 if recording is active
        if cam_id == 1:
            self.recorder.write_frame(frame)

    def update_sensors(self, data):
        """
        Called when new sensor data is received.
        Updates the sensor display labels.
        """
        humidity = data.get('humidity', 0)
        current = data.get('current', 0)

        self.Humidity_Data.setText(f"Humidity: {humidity} %")
        self.Current_Data.setText(f"Current: {current} A")

    def keyPressEvent(self, event):
        """
        Handle keyboard input.
        C - Start recording
        S - Stop recording
        """
        key = event.key()

        if key == Qt.Key.Key_C:
            print("Starting camera recording...")
            self.recorder.start_recording()

        elif key == Qt.Key.Key_S:
            print("Stopping camera recording...")
            self.recorder.stop_recording()

    def closeEvent(self, event):
        """
        Clean up when the window is closed.
        """
        print("\nShutting down ROV control system...")

        # Stop all threads
        if hasattr(self, 'control_thread'):
            self.control_thread.stop()

        if hasattr(self, 'sensor_ws_thread'):
            self.sensor_ws_thread.stop()

        # Close camera receiver
        if hasattr(self, 'camera_receiver'):
            self.camera_receiver.close()

        # Stop sensor client
        if hasattr(self, 'sensor_client'):
            self.sensor_client.stop()

        print("Shutdown complete")
        event.accept()


if __name__ == "__main__":
    print("\n" + "="*50)
    print("STARTING ROV CONTROL SYSTEM")
    print("="*50 + "\n")

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()

    # Run the application
    sys.exit(app.exec())
