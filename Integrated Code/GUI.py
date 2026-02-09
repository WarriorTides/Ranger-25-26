#!/usr/bin/env python3
"""
ROV GUI Application
Displays 3 camera feeds, sensor data, and claw state
Recording controls: R to start, S to stop
"""

import sys
import os
import socket
import json
import base64
import time
from PyQt6.QtWidgets import QApplication, QMainWindow, QSizePolicy, QLabel
from PyQt6 import uic
from PyQt6.QtCore import QTimer, Qt, QObject, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap
import cv2
import PyQt6
import asyncio
import websockets
import json
import threading

# Fix Qt platform plugin path
plugin_path = os.path.join(os.path.dirname(PyQt6.__file__), "Qt6", "plugins", "platforms")
os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = plugin_path


# ============================================================================
# SENSOR CLIENT (WebSocket)
# ============================================================================
class SensorClient(QObject):
    """WebSocket client for receiving sensor data and claw state"""
    data_received = pyqtSignal(dict)
    
    def __init__(self, ws_url="ws://192.168.2.10:8765"):
        super().__init__()
        self.ws_url = ws_url
        self.running = True
        self.thread = None
    
    def start(self):
        """Start the WebSocket client in a separate thread"""
        self.thread = threading.Thread(target=self._run_async_loop, daemon=True)
        self.thread.start()
        print(f"Sensor client connecting to {self.ws_url}")
    
    def _run_async_loop(self):
        """Run the async event loop in the thread"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._connect())
    
    async def _connect(self):
        """Connect to WebSocket and receive data"""
        while self.running:
            try:
                async with websockets.connect(self.ws_url) as websocket:
                    print("Connected to ROV control server")
                    
                    async for message in websocket:
                        try:
                            data = json.loads(message)
                            self.data_received.emit(data)
                        except json.JSONDecodeError:
                            print(f"Invalid JSON: {message}")
            
            except Exception as e:
                print(f"WebSocket error: {e}")
                await asyncio.sleep(2)  # Wait before reconnecting
    
    def stop(self):
        """Stop the WebSocket client"""
        self.running = False


# ============================================================================
# CAMERA RECEIVER (UDP)
# ============================================================================
class CameraReceiver(QObject):
    """Receives frames from camera server via UDP"""
    frame_received = pyqtSignal(int, object)  # (camera_id, frame)
    
    def __init__(self, camera_ports=None):
        super().__init__()
        
        # Default camera ports
        if camera_ports is None:
            camera_ports = [5005, 5006, 5007]  # Ports for cameras 1, 2, 3
        
        self.camera_ports = camera_ports
        self.sockets = []
        self.last_frame_time = {}
        self.frame_count = {}
        
        # Initialize UDP sockets for each camera
        for cam_id, port in enumerate(camera_ports, start=1):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.bind(("", port))
                sock.settimeout(0.01)  # Non-blocking with short timeout
                self.sockets.append((cam_id, sock, port))
                self.last_frame_time[cam_id] = 0
                self.frame_count[cam_id] = 0
                print(f"Camera {cam_id} receiver bound to UDP port {port}")
            except Exception as e:
                print(f"Failed to bind camera {cam_id} on port {port}: {e}")
                self.sockets.append((cam_id, None, port))
    
    def poll(self):
        """Poll all UDP sockets for camera frames"""
        for cam_id, sock, port in self.sockets:
            if sock is None:
                # No socket, show test pattern
                frame = self._generate_test_frame(cam_id)
                self.frame_received.emit(cam_id, frame)
                continue
            
            try:
                # Try to receive data
                data, addr = sock.recvfrom(65536)  # Large buffer for JPEG data
                
                # Parse JSON message
                try:
                    msg = json.loads(data.decode('utf-8'))
                    
                    if msg.get("type") == "camera":
                        # Decode base64 image
                        jpg_data = base64.b64decode(msg["data"])
                        
                        # Convert to numpy array
                        import numpy as np
                        nparr = np.frombuffer(jpg_data, np.uint8)
                        
                        # Decode JPEG
                        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                        
                        if frame is not None:
                            self.frame_received.emit(cam_id, frame)
                            self.frame_count[cam_id] += 1
                            self.last_frame_time[cam_id] = time.time()
                        else:
                            # Failed to decode
                            if self.frame_count[cam_id] == 0:
                                frame = self._generate_test_frame(cam_id, "DECODE ERROR")
                                self.frame_received.emit(cam_id, frame)
                
                except json.JSONDecodeError:
                    # Invalid JSON
                    if self.frame_count[cam_id] == 0:
                        frame = self._generate_test_frame(cam_id, "INVALID DATA")
                        self.frame_received.emit(cam_id, frame)
            
            except socket.timeout:
                # No data received, check if we should show test pattern
                time_since_last = time.time() - self.last_frame_time.get(cam_id, 0)
                if time_since_last > 2.0 or self.frame_count[cam_id] == 0:
                    # No frames for 2 seconds, show "NO SIGNAL"
                    frame = self._generate_test_frame(cam_id, "NO SIGNAL")
                    self.frame_received.emit(cam_id, frame)
            
            except Exception as e:
                # Other error
                print(f"Camera {cam_id} error: {e}")
                frame = self._generate_test_frame(cam_id, f"ERROR: {str(e)[:20]}")
                self.frame_received.emit(cam_id, frame)
    
    def _generate_test_frame(self, cam_id, message="NO SIGNAL"):
        """Generate a test frame with camera ID and message"""
        import numpy as np
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        
        # Add colored background based on camera ID
        colors = {1: (50, 0, 0), 2: (0, 50, 0), 3: (0, 0, 50)}
        frame[:] = colors.get(cam_id, (30, 30, 30))
        
        # Add text
        text = f"Camera {cam_id}"
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(frame, text, (80, 120), font, 1, (255, 255, 255), 2)
        cv2.putText(frame, message, (70, 160), font, 0.6, (200, 200, 200), 1)
        
        # Add timestamp
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        cv2.putText(frame, timestamp, (10, 230), font, 0.4, (150, 150, 150), 1)
        
        return frame
    
    def cleanup(self):
        """Close all UDP sockets"""
        for cam_id, sock, port in self.sockets:
            if sock:
                sock.close()
                print(f"Camera {cam_id} socket closed")


# ============================================================================
# CAMERA RECORDER
# ============================================================================
class CameraRecorder:
    """Records video from camera feed"""
    
    def __init__(self, frame_size=(320, 240), fps=20.0):
        self.frame_size = frame_size
        self.fps = fps
        self.writer = None
        self.recording = False
        self.filename = None
    
    def start_recording(self):
        """Start recording to a new file"""
        if self.recording:
            print("Already recording!")
            return
        
        # Generate filename with timestamp
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.filename = f"rov_recording_{timestamp}.avi"
        
        # Create video writer
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        self.writer = cv2.VideoWriter(self.filename, fourcc, self.fps, self.frame_size)
        
        if self.writer.isOpened():
            self.recording = True
            print(f"🔴 Recording started: {self.filename}")
            return True
        else:
            print("Failed to start recording!")
            self.writer = None
            return False
    
    def stop_recording(self):
        """Stop recording and save the file"""
        if not self.recording:
            print("Not currently recording!")
            return
        
        self.recording = False
        if self.writer:
            self.writer.release()
            self.writer = None
            print(f"⏹️  Recording stopped: {self.filename}")
            print(f"   File saved to: {os.path.abspath(self.filename)}")
    
    def write_frame(self, frame):
        """Write a frame to the recording"""
        if self.recording and self.writer:
            # Ensure frame is the correct size
            if frame.shape[:2] != self.frame_size[::-1]:
                frame = cv2.resize(frame, self.frame_size)
            self.writer.write(frame)
    
    def is_recording(self):
        """Check if currently recording"""
        return self.recording


# ============================================================================
# MAIN WINDOW
# ============================================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Try to load UI file, fallback to programmatic creation
        ui_path = "/Users/kashishkapoor/Desktop/Mate_ROV.ui"
        
        if os.path.exists(ui_path):
            uic.loadUi(ui_path, self)
            print(f"UI loaded from {ui_path}")
        else:
            print(f"UI file not found: {ui_path}")
            print("Creating UI programmatically...")
            self._create_ui_programmatically()
        
        # Setup camera feeds
        self._setup_camera_labels()
        
        # Initialize camera receiver
        self.camera_receiver = CameraReceiver()
        self.camera_receiver.frame_received.connect(self.update_camera)
        
        # Poll cameras at ~30 FPS
        self.camera_timer = QTimer()
        self.camera_timer.timeout.connect(self.camera_receiver.poll)
        self.camera_timer.start(33)  # ~30 FPS
        
        # Initialize recorder
        self.recorder = CameraRecorder(frame_size=(320, 240))
        
        # Initialize sensor client
        self.sensor_client = SensorClient(ws_url="ws://192.168.2.10:8765")
        self.sensor_client.data_received.connect(self.update_data)
        self.sensor_client.start()
        
        # Claw state (for display)
        self.claw_state = {
            "claw1_angle": 0,
            "claw1_rotation": 0,
            "claw2_angle": 0,
            "claw2_rotation": 0,
        }
        
        print("\n" + "=" * 60)
        print("ROV GUI STARTED")
        print("=" * 60)
        print("Controls:")
        print("  R - Start recording")
        print("  S - Stop recording")
        print("=" * 60 + "\n")
    
    def _create_ui_programmatically(self):
        """Create UI elements programmatically if .ui file is missing"""
        from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        
        # Camera feeds
        camera_layout = QHBoxLayout()
        self.Camera_Feed_1 = QLabel("Camera 1")
        self.Camera_Feed_2 = QLabel("Camera 2")
        self.Camera_Feed_3 = QLabel("Camera 3")
        
        camera_layout.addWidget(self.Camera_Feed_1)
        camera_layout.addWidget(self.Camera_Feed_2)
        camera_layout.addWidget(self.Camera_Feed_3)
        
        main_layout.addLayout(camera_layout)
        
        # Sensor data
        sensor_layout = QHBoxLayout()
        self.Humidity_Data = QLabel("Humidity: -- %")
        self.Current_Data = QLabel("Current: -- A")
        
        sensor_layout.addWidget(self.Humidity_Data)
        sensor_layout.addWidget(self.Current_Data)
        
        main_layout.addLayout(sensor_layout)
        
        # Claw data
        claw_layout = QHBoxLayout()
        self.Claw1_Data = QLabel("Claw 1: 0° / 0°")
        self.Claw2_Data = QLabel("Claw 2: 0° / 0°")
        
        claw_layout.addWidget(self.Claw1_Data)
        claw_layout.addWidget(self.Claw2_Data)
        
        main_layout.addLayout(claw_layout)
        
        # Recording status
        self.Recording_Status = QLabel("⚪ Not Recording")
        main_layout.addWidget(self.Recording_Status)
        
        self.setWindowTitle("ROV Control Interface")
        self.resize(1000, 600)
    
    def _setup_camera_labels(self):
        """Configure camera feed labels"""
        camera_labels = [self.Camera_Feed_1, self.Camera_Feed_2, self.Camera_Feed_3]
        
        for label in camera_labels:
            label.setScaledContents(True)
            label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            label.setMinimumSize(320, 240)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("background-color: black; border: 2px solid #333;")
    
    def update_camera(self, cam_id, frame):
        """Update camera feed display"""
        # Convert BGR to RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame_rgb.shape
        
        # Create QImage and QPixmap
        qimg = QImage(frame_rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
        pix = QPixmap.fromImage(qimg)
        
        # Display on appropriate label
        label_map = {
            1: self.Camera_Feed_1,
            2: self.Camera_Feed_2,
            3: self.Camera_Feed_3
        }
        
        label = label_map.get(cam_id)
        if label:
            label.setPixmap(pix)
        
        # Record camera 1 if recording
        if cam_id == 1:
            self.recorder.write_frame(frame)
    
    def update_data(self, data):
        """Update sensor data and claw state from WebSocket"""
        data_type = data.get("type", "unknown")
        
        if data_type == "sensor":
            # Update sensor displays
            if "humidity" in data:
                humidity = data["humidity"]
                self.Humidity_Data.setText(f"💧 Humidity: {humidity:.1f}%")
            
            if "current" in data:
                current = data["current"]
                self.Current_Data.setText(f"⚡ Current: {current:.2f}A")
        
        elif data_type == "claw_state":
            # Update claw state
            self.claw_state = {
                "claw1_angle": data.get("claw1_angle", 0),
                "claw1_rotation": data.get("claw1_rotation", 0),
                "claw2_angle": data.get("claw2_angle", 0),
                "claw2_rotation": data.get("claw2_rotation", 0),
            }
            
            # Update claw displays
            if hasattr(self, 'Claw1_Data'):
                self.Claw1_Data.setText(
                    f"🦾 Claw 1: {self.claw_state['claw1_angle']}° / {self.claw_state['claw1_rotation']}° rot"
                )
            
            if hasattr(self, 'Claw2_Data'):
                self.Claw2_Data.setText(
                    f"🦾 Claw 2: {self.claw_state['claw2_angle']}° / {self.claw_state['claw2_rotation']}° rot"
                )
    
    def keyPressEvent(self, event):
        """Handle keyboard events for recording control"""
        key = event.key()
        
        if key == Qt.Key.Key_R:
            # Start recording
            if not self.recorder.is_recording():
                if self.recorder.start_recording():
                    if hasattr(self, 'Recording_Status'):
                        self.Recording_Status.setText("RECORDING")
                        self.Recording_Status.setStyleSheet("color: red; font-weight: bold;")
        
        elif key == Qt.Key.Key_S:
            # Stop recording
            if self.recorder.is_recording():
                self.recorder.stop_recording()
                if hasattr(self, 'Recording_Status'):
                    self.Recording_Status.setText("⚪ Not Recording")
                    self.Recording_Status.setStyleSheet("color: gray;")
        
        elif key == Qt.Key.Key_Escape:
            # Exit application
            self.close()
    
    def closeEvent(self, event):
        """Clean up when window is closed"""
        print("Shutting down GUI...")
        
        # Stop recording if active
        if self.recorder.is_recording():
            self.recorder.stop_recording()
        
        # Stop sensor client
        self.sensor_client.stop()
        
        # Release cameras
        self.camera_receiver.cleanup()
        
        event.accept()


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())