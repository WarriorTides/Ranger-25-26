import cv2
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal
import time

class CameraReceiver(QObject):
    frame_received = pyqtSignal(int, object)  

    def __init__(self):
        super().__init__()
        self.counter = 0

    def poll(self):
        """Simulate 3 camera feeds with changing colors"""
        # for cam_id in range(1, 4):
        #     frame = np.zeros((240, 320, 3), dtype=np.uint8)
        #     color = [(255,0,0), (0,255,0), (0,0,255)][cam_id-1]
        #     frame[:] = (self.counter % 255, *color[1:])
        #     self.frame_received.emit(cam_id, frame)
        # self.counter += 5
        # time.sleep(0.03)
        pass