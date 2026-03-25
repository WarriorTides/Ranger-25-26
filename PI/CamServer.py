

import cv2
import socket
import struct
import time
import threading

PC_IP = "192.168.1.119"
PORTS = [5005, 5006, 5007]
CAMERA_IDS = [0, 4, 8]
TARGET_FPS = 15
FRAME_W = 320
FRAME_H = 240
JPEG_QUALITY = 50
HEADER_FMT = ">BI"
HEADER_SIZE = struct.calcsize(HEADER_FMT)


def make_header(cam_id: int, payload_len: int) -> bytes:
    return struct.pack(HEADER_FMT, cam_id, payload_len)


def camera_loop(cam_idx: int, cam_device: int):
    """Capture → encode → send loop for one camera."""
    port = PORTS[cam_idx]
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
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    encode_params = [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY]
    frame_interval = 1.0 / TARGET_FPS
    dest = (PC_IP, port)

    print(f"[Cam {cam_idx+1}] Streaming device {cam_device} → {PC_IP}:{port}")

    while True:
        t0 = time.monotonic()

        ret, frame = cap.read()
        if not ret:
            print(f"[Cam {cam_idx+1}] Read failed, retrying...")
            time.sleep(0.1)
            continue

        ok, buf = cv2.imencode(".jpg", frame, encode_params)
        if not ok:
            continue

        jpg_bytes = buf.tobytes()
        header = make_header(cam_idx + 1, len(jpg_bytes))
        packet = header + jpg_bytes
        try:
            sock.sendto(packet, dest)
        except Exception as e:
            print(f"[Cam {cam_idx+1}] Send error: {e}")

        elapsed = time.monotonic() - t0
        remaining = frame_interval - elapsed
        if remaining > 0:
            time.sleep(remaining)


def main():
    if len(CAMERA_IDS) > len(PORTS):
        print("ERROR: More cameras than ports defined")
        return

    threads = []
    for idx, dev in enumerate(CAMERA_IDS):
        t = threading.Thread(target=camera_loop, args=(idx, dev), daemon=True)
        t.start()
        threads.append(t)
        time.sleep(0.1)   # stagger starts slightly to reduce burst at t=0

    print(f"Streaming {len(CAMERA_IDS)} cameras at {TARGET_FPS}fps "
          f"({FRAME_W}x{FRAME_H}, JPEG q={JPEG_QUALITY}). Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")


if __name__ == "__main__":
    main()
