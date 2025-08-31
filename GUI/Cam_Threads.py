from PyQt6.QtCore import QThread, pyqtSignal
import cv2

class CameraThread(QThread):
    frame_received = pyqtSignal(object)  
    def __init__(self, camera_index=0):
        super().__init__()
        self.camera_index = camera_index
        self.running = True
    def run(self):
        cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            print("Error: Can't open the cam")
            return    
        while self.running:
            ret, frame = cap.read()
            if ret:
                self.frame_received.emit(frame)  
            else:
                print("Error: Can't read frame")
                break
        cap.release()
    def stop(self):
        self.running = False
        self.wait()  