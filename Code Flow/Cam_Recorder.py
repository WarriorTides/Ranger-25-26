# import cv2
# import os
# import queue
# import threading
# from datetime import datetime


# class CameraRecorder:

#     def __init__(self, fps=20, frame_size=(320, 240)):
#         self.fps = fps
#         self.frame_size = frame_size
#         self.writer = None
#         self.recording = False

#         # Background write thread — keeps disk I/O off the main thread
#         self._queue: queue.Queue = queue.Queue(maxsize=10)
#         self._thread = threading.Thread(
#             target=self._write_loop, daemon=True, name="RecorderThread"
#         )
#         self._thread.start()

#         downloads = os.path.join(os.path.expanduser("~"), "Downloads")
#         os.makedirs(downloads, exist_ok=True)
#         timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#         self.save_path = os.path.join(
#             downloads, f"rov_recording_{timestamp}.avi")

#     def start_recording(self):
#         if not self.recording:
#             self.writer = cv2.VideoWriter(
#                 self.save_path,
#                 cv2.VideoWriter_fourcc(*"mp4v"),
#                 self.fps,
#                 self.frame_size,
#             )
#             self.recording = True
#             print(f"[Recorder] Started: {self.save_path}")

#     def write_frame(self, frame_bgr):
#         """Called from main thread — just enqueues, never blocks."""
#         if not self.recording or self.writer is None:
#             return
#         try:
#             # Drop frame if queue is full rather than blocking the main thread
#             self._queue.put_nowait(frame_bgr)
#         except queue.Full:
#             pass  # silently drop — better than freezing the UI

#     def stop_recording(self):
#         if self.recording:
#             self.recording = False
#             # Flush remaining frames before releasing
#             self._queue.join()
#             self.writer.release()
#             self.writer = None
#             print(f"[Recorder] Saved: {self.save_path}")

#     def _write_loop(self):
#         """Runs on background thread — does all actual disk writes."""
#         while True:
#             frame = self._queue.get()
#             try:
#                 if self.writer is not None:
#                     h, w = frame.shape[:2]
#                     if (w, h) != self.frame_size:
#                         frame = cv2.resize(frame, self.frame_size)
#                     self.writer.write(frame)
#             except Exception as e:
#                 print(f"[Recorder] Write error: {e}")
#             finally:
#                 self._queue.task_done()


# ------#

import cv2
import os
import queue
import threading
from datetime import datetime

_SENTINEL = object()  # signals the write loop to flush and stop waiting


class CameraRecorder:

    def __init__(self, fps=20, frame_size=(320, 240)):
        self.fps = fps
        self.frame_size = frame_size
        self.writer = None
        self.recording = False

        # Background write thread — keeps disk I/O off the main thread.
        # maxsize=30 gives ~1.5 s of buffer at 20 fps before dropping,
        # which is enough headroom for brief disk stalls without building
        # up unbounded memory.
        self._queue: queue.Queue = queue.Queue(maxsize=30)
        self._thread = threading.Thread(
            target=self._write_loop, daemon=True, name="RecorderThread"
        )
        self._thread.start()

        downloads = os.path.join(os.path.expanduser("~"), "Downloads")
        os.makedirs(downloads, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.save_path = os.path.join(
            downloads, f"rov_recording_{timestamp}.avi"
        )

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
        """Called from main thread — just enqueues, never blocks."""
        if not self.recording or self.writer is None:
            return
        try:
            self._queue.put_nowait(frame_bgr)
        except queue.Full:
            pass

    def stop_recording(self):
        """
        Non-blocking stop: sends a sentinel so the write thread finishes
        whatever is already queued, then releases the writer.  This method
        returns immediately — no join(), no UI freeze.
        """
        if not self.recording:
            return
        self.recording = False
        # Sentinel tells _write_loop to flush remaining frames then release.
        try:
            self._queue.put(_SENTINEL, timeout=0.5)
        except queue.Full:
            # Queue is full of frames we can't flush — force-release.
            self._force_release()
        print(f"[Recorder] Stop requested — flushing to {self.save_path}")

    def _force_release(self):
        if self.writer is not None:
            self.writer.release()
            self.writer = None
            print("[Recorder] Writer force-released (queue was full)")

    def _write_loop(self):
        """Runs on background thread — all disk writes happen here."""
        while True:
            try:
                item = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue

            if item is _SENTINEL:
                # Drain everything still in the queue before releasing.
                while True:
                    try:
                        frame = self._queue.get_nowait()
                        if frame is _SENTINEL:
                            break
                        self._write_one(frame)
                    except queue.Empty:
                        break
                if self.writer is not None:
                    self.writer.release()
                    self.writer = None
                print(f"[Recorder] Saved: {self.save_path}")
                continue  # keep thread alive for a future start_recording()

            self._write_one(item)

    def _write_one(self, frame):
        try:
            if self.writer is not None:
                h, w = frame.shape[:2]
                if (w, h) != self.frame_size:
                    frame = cv2.resize(frame, self.frame_size)
                self.writer.write(frame)
        except Exception as e:
            print(f"[Recorder] Write error: {e}")
