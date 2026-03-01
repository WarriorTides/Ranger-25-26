import cv2
import os
from datetime import datetime


class CameraRecorder:

    def __init__(self, fps=20, frame_size=(320, 240)):
        self.fps = fps
        self.frame_size = frame_size
        self.writer = None
        self.recording = False

        downloads = os.path.join(os.path.expanduser("~"), "Downloads")
        os.makedirs(downloads, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.save_path = os.path.join(
            downloads, f"rov_recording_{timestamp}.avi")

    def start_recording(self):
        if not self.recording:
            self.writer = cv2.VideoWriter(
                self.save_path,
                cv2.VideoWriter_fourcc(*"mp4v"),
                self.fps,
                self.frame_size,
            )
            self.recording = True
            print(f"[Recorder] Started: {self.save_path}")

    def write_frame(self, frame_bgr):
        if not self.recording or self.writer is None:
            return
        h, w = frame_bgr.shape[:2]
        if (w, h) != self.frame_size:
            frame_bgr = cv2.resize(frame_bgr, self.frame_size)
        self.writer.write(frame_bgr)

    def stop_recording(self):
        if self.recording:
            self.writer.release()
            self.writer = None
            self.recording = False
            print(f"[Recorder] Saved: {self.save_path}")
