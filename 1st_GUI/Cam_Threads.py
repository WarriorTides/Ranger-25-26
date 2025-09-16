from PyQt6.QtCore import QThread, pyqtSignal
import cv2

class CameraThread(QThread):
    frame_updated = pyqtSignal(object)  

    def __init__(self, camera_index=0):
        super().__init__()
        self.camera_index = camera_index
        self.running = True

    def run(self):
        cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            print(f"Error: Can't open camera {self.camera_index}")
            return    

        while self.running:
            ret, frame = cap.read()
            if ret:
                self.frame_updated.emit(frame)  
            else:
                print(f"Error: Can't read frame from camera {self.camera_index}")
                break

        cap.release()

    def stop(self):
        self.running = False
        self.quit()  
        self.wait()
