# """
# cam_sender.py — Optimized ROV camera streamer

# Key improvements over original:
# - Raw JPEG bytes sent directly (no Base64, no JSON) → ~33% smaller packets
# - Adaptive frame timing: measures encode+send time and sleeps only the remainder
# - Per-camera thread with its own socket
# - Camera opened with V4L2 backend on Linux for lower latency (falls back gracefully)
# - JPEG quality reduced to 50 (barely visible difference at 320x240, much faster)
# - Frame is captured, encoded, and sent in a tight loop — no artificial sleep drift
# """

# import cv2
# import socket
# import struct
# import time
# import threading

# # ── Configuration ────────────────────────────────────────────────────────────

# PC_IP = "192.168.1.119"
# PORTS = [5005, 5006, 5007]
# CAMERA_IDS = [0, 4, 8]          # adjust to your actual camera indices
# TARGET_FPS = 15
# FRAME_W = 320
# FRAME_H = 240
# # 40-60 is plenty for FPV; cuts packet size nearly in half
# JPEG_QUALITY = 50

# # ── Packet format ─────────────────────────────────────────────────────────────
# #
# #  [ 1 byte cam_id ][ 4 bytes payload_len (big-endian) ][ N bytes JPEG ]
# #
# #  Total overhead: 5 bytes vs ~200+ bytes for JSON+Base64 wrapper.
# #  The receiver must be updated to match (see CamReceiver below).

# HEADER_FMT = ">BI"   # unsigned char + unsigned int
# HEADER_SIZE = struct.calcsize(HEADER_FMT)   # 5 bytes


# def make_header(cam_id: int, payload_len: int) -> bytes:
#     return struct.pack(HEADER_FMT, cam_id, payload_len)


# # ── Per-camera streaming thread ───────────────────────────────────────────────

# def camera_loop(cam_idx: int, cam_device: int):
#     """Capture → encode → send loop for one camera."""
#     port = PORTS[cam_idx]
#     sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#     # Increase OS send buffer to handle bursts without blocking
#     sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 524288)

#     # Try V4L2 backend first (Linux) for lower capture latency
#     cap = cv2.VideoCapture(cam_device, cv2.CAP_V4L2)
#     if not cap.isOpened():
#         cap = cv2.VideoCapture(cam_device)   # fallback for macOS/Windows

#     if not cap.isOpened():
#         print(f"[Cam {cam_idx+1}] ERROR: Could not open device {cam_device}")
#         return

#     cap.set(cv2.CAP_PROP_FRAME_WIDTH,  FRAME_W)
#     cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_H)
#     cap.set(cv2.CAP_PROP_FPS,          TARGET_FPS)
#     # Minimize OpenCV's internal capture buffer — we only want the latest frame
#     cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

#     encode_params = [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY]
#     frame_interval = 1.0 / TARGET_FPS
#     dest = (PC_IP, port)

#     print(f"[Cam {cam_idx+1}] Streaming device {cam_device} → {PC_IP}:{port}")

#     while True:
#         t0 = time.monotonic()

#         ret, frame = cap.read()
#         if not ret:
#             print(f"[Cam {cam_idx+1}] Read failed, retrying...")
#             time.sleep(0.1)
#             continue

#         ok, buf = cv2.imencode(".jpg", frame, encode_params)
#         if not ok:
#             continue

#         jpg_bytes = buf.tobytes()
#         header = make_header(cam_idx + 1, len(jpg_bytes))
#         packet = header + jpg_bytes

#         # UDP max safe payload is ~65507 bytes; a 320x240 JPEG at q=50
#         # is typically 5–12KB so we're well within limits.
#         try:
#             sock.sendto(packet, dest)
#         except Exception as e:
#             print(f"[Cam {cam_idx+1}] Send error: {e}")

#         # Sleep only the time remaining in this frame slot
#         elapsed = time.monotonic() - t0
#         remaining = frame_interval - elapsed
#         if remaining > 0:
#             time.sleep(remaining)


# # ── Entry point ───────────────────────────────────────────────────────────────

# def main():
#     if len(CAMERA_IDS) > len(PORTS):
#         print("ERROR: More cameras than ports defined")
#         return

#     threads = []
#     for idx, dev in enumerate(CAMERA_IDS):
#         t = threading.Thread(target=camera_loop, args=(idx, dev), daemon=True)
#         t.start()
#         threads.append(t)
#         time.sleep(0.1)   # stagger starts slightly to reduce burst at t=0

#     print(f"Streaming {len(CAMERA_IDS)} cameras at {TARGET_FPS}fps "
#           f"({FRAME_W}x{FRAME_H}, JPEG q={JPEG_QUALITY}). Ctrl+C to stop.")

#     try:
#         while True:
#             time.sleep(1)
#     except KeyboardInterrupt:
#         print("\nShutting down...")


# if __name__ == "__main__":
#     main()


"""
cam_sender.py — ROV camera streamer (lag-fixed)

Changes from previous version:
- FIX #2  Absolute-deadline frame loop — no drift accumulation.
          Old code: sleep(remaining) which drifts when encode takes variable time.
          New code: tracks a hard deadline and always sleeps to the next slot,
          catching up automatically if a frame ran long.
- FIX #5  Per-camera JPEG quality — cameras 2 & 3 drop to q=35 since they're
          secondary feeds.  Cuts encode time and packet size on those streams.
"""

import cv2
import socket
import struct
import time
import threading

# ── Configuration ─────────────────────────────────────────────────────────────

PC_IP = "192.168.1.119"
PORTS = [5005, 5006, 5007]
CAMERA_IDS = [0, 4, 8]          # adjust to your actual camera indices
TARGET_FPS = 15
FRAME_W = 320
FRAME_H = 240

# FIX #5 — lower quality for secondary feeds
JPEG_QUALITY_PER_CAM = {
    0: 50,   # cam 1 — primary, keep quality
    1: 35,   # cam 2 — secondary
    2: 35,   # cam 3 — secondary
}

# ── Packet format ─────────────────────────────────────────────────────────────
#   [ 1 byte cam_id ][ 4 bytes payload_len big-endian ][ N bytes JPEG ]

HEADER_FMT = ">BI"
HEADER_SIZE = struct.calcsize(HEADER_FMT)   # 5 bytes


def make_header(cam_id: int, payload_len: int) -> bytes:
    return struct.pack(HEADER_FMT, cam_id, payload_len)


# ── Per-camera streaming thread ───────────────────────────────────────────────

def camera_loop(cam_idx: int, cam_device: int):
    """Capture → encode → send loop for one camera."""
    port = PORTS[cam_idx]
    quality = JPEG_QUALITY_PER_CAM.get(cam_idx, 50)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 524288)

    cap = cv2.VideoCapture(cam_device, cv2.CAP_V4L2)
    if not cap.isOpened():
        cap = cv2.VideoCapture(cam_device)

    if not cap.isOpened():
        print(f"[Cam {cam_idx+1}] ERROR: Could not open device {cam_device}")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  FRAME_W)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_H)
    cap.set(cv2.CAP_PROP_FPS,          TARGET_FPS)
    cap.set(cv2.CAP_PROP_BUFFERSIZE,   1)

    encode_params = [cv2.IMWRITE_JPEG_QUALITY, quality]
    frame_interval = 1.0 / TARGET_FPS
    dest = (PC_IP, port)

    print(f"[Cam {cam_idx+1}] Streaming device {cam_device} → {PC_IP}:{port} "
          f"(JPEG q={quality})")

    # FIX #2 — absolute deadline: set the first deadline now, then advance it
    # by exactly frame_interval each iteration regardless of how long work took.
    # If a frame runs over, the next sleep is shorter (or zero) — we catch up
    # instead of drifting further behind like the old time.monotonic()-sleep did.
    deadline = time.monotonic()

    while True:
        deadline += frame_interval

        ret, frame = cap.read()
        if not ret:
            print(f"[Cam {cam_idx+1}] Read failed, retrying...")
            # Reset deadline after a stall so we don't spin trying to catch up
            deadline = time.monotonic()
            time.sleep(0.1)
            continue

        ok, buf = cv2.imencode(".jpg", frame, encode_params)
        if not ok:
            continue

        jpg_bytes = buf.tobytes()
        packet = make_header(cam_idx + 1, len(jpg_bytes)) + jpg_bytes

        try:
            sock.sendto(packet, dest)
        except Exception as e:
            print(f"[Cam {cam_idx+1}] Send error: {e}")

        # Sleep only the time remaining until the next hard deadline
        remaining = deadline - time.monotonic()
        if remaining > 0:
            time.sleep(remaining)
        # If remaining <= 0 we're already behind — skip the sleep and start
        # the next frame immediately.  deadline still advances by frame_interval
        # so one slow frame doesn't cascade into permanent lag.


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    if len(CAMERA_IDS) > len(PORTS):
        print("ERROR: More cameras than ports defined")
        return

    threads = []
    for idx, dev in enumerate(CAMERA_IDS):
        t = threading.Thread(target=camera_loop, args=(idx, dev), daemon=True)
        t.start()
        threads.append(t)
        time.sleep(0.1)

    print(f"Streaming {len(CAMERA_IDS)} cameras at {TARGET_FPS}fps "
          f"({FRAME_W}x{FRAME_H}). Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")


if __name__ == "__main__":
    main()
