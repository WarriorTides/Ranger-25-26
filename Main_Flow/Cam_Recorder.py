import cv2
import os
import queue
import threading
from datetime import datetime


class CameraRecorder:

    def __init__(self, fps=20, frame_size=(320, 240)):
        self.fps = fps
        self.frame_size = frame_size
        self.writer = None
        self.recording = False

        self._queue: queue.Queue = queue.Queue(maxsize=10)
        self._thread = threading.Thread(
            target=self._write_loop, daemon=True, name="RecorderThread"
        )
        self._thread.start()

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
        """Called from main thread — enqueues only, never blocks."""
        if not self.recording or self.writer is None:
            return
        try:
            self._queue.put_nowait(frame_bgr)
        except queue.Full:
            pass  # drop frame rather than stall UI

    def stop_recording(self):
        """
        FIX: Original used queue.join() which could deadlock the main thread
        if the write loop was stuck. Now we drain with a timeout and clear
        any remaining frames before releasing the writer.
        """
        if not self.recording:
            return

        self.recording = False

        # Give the write loop up to 2 seconds to flush naturally
        deadline = threading.Event()

        def _wait():
            self._queue.join()
            deadline.set()

        waiter = threading.Thread(target=_wait, daemon=True)
        waiter.start()
        deadline.wait(timeout=2.0)

        # Clear anything left so task_done counts stay balanced
        while True:
            try:
                self._queue.get_nowait()
                self._queue.task_done()
            except queue.Empty:
                break

        if self.writer:
            self.writer.release()
            self.writer = None
            print(f"[Recorder] Saved: {self.save_path}")

    def _write_loop(self):
        """Background thread — all disk I/O happens here."""
        while True:
            frame = self._queue.get()
            try:
                if self.writer is not None:
                    h, w = frame.shape[:2]
                    if (w, h) != self.frame_size:
                        frame = cv2.resize(frame, self.frame_size)
                    self.writer.write(frame)
            except Exception as e:
                print(f"[Recorder] Write error: {e}")
            finally:
                self._queue.task_done()
