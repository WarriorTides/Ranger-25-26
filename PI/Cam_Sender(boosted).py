"""
cam_sender.py  —  runs on the Raspberry Pi
Streams 3 cameras at low resolution normally.
Listens on CONTROL_PORT (UDP) for boost/drop commands from the PC.

Command format  (PC → Pi, plain text):
  "boost:1"   →  camera 1 switches to high-res for BOOST_DURATION seconds
  "boost:2"   →  camera 2, etc.
  "drop:1"    →  immediately revert camera 1 (optional; auto-reverts anyway)

Resolution modes:
  LOW  : 320×240, q=50, 15 fps   ← always-on for all 3 cams
  HIGH : 640×480, q=80, 10 fps   ← temporary boost for one cam
"""

import cv2
import socket
import struct
import time
import threading

# ── Network ──────────────────────────────────────────────────────────────────
PC_IP = "192.168.1.119"
PORTS = [5005, 5006, 5007]
CONTROL_PORT = 5010          # PC sends boost/drop commands here

# ── Camera devices ────────────────────────────────────────────────────────────
CAMERA_IDS = [0, 4, 8]       # adjust to your actual /dev/videoX indices

# ── Low-res defaults (always-on) ──────────────────────────────────────────────
LOW_W = 320
LOW_H = 240
LOW_FPS = 15
LOW_QUAL = 50

# ── High-res boost ────────────────────────────────────────────────────────────
HIGH_W = 640
HIGH_H = 480
HIGH_FPS = 10          # drop fps to keep packets from piling up
HIGH_QUAL = 80
BOOST_DURATION = 5.0         # seconds before auto-revert

# ── Packet header ─────────────────────────────────────────────────────────────
HEADER_FMT = ">BI"
HEADER_SIZE = struct.calcsize(HEADER_FMT)


def make_header(cam_id: int, payload_len: int) -> bytes:
    return struct.pack(HEADER_FMT, cam_id, payload_len)


# ── Per-camera boost state ─────────────────────────────────────────────────────
# boosted[cam_idx] = monotonic time when boost expires, or 0.0 if not boosted
_boost_lock = threading.Lock()
_boost_expiry = [0.0, 0.0, 0.0]   # indexed 0-2


def _is_boosted(cam_idx: int) -> bool:
    with _boost_lock:
        return time.monotonic() < _boost_expiry[cam_idx]


def _set_boost(cam_idx: int, active: bool):
    with _boost_lock:
        if active:
            _boost_expiry[cam_idx] = time.monotonic() + BOOST_DURATION
            print(f"[Sender] Cam {cam_idx+1} → HIGH-RES for {BOOST_DURATION}s")
        else:
            _boost_expiry[cam_idx] = 0.0
            print(f"[Sender] Cam {cam_idx+1} → low-res (manual drop)")


# ── Control listener thread ────────────────────────────────────────────────────
def _control_listener():
    """Listens for boost/drop UDP commands from the PC."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", CONTROL_PORT))
    sock.settimeout(1.0)
    print(f"[Sender] Control listener on UDP :{CONTROL_PORT}")
    while True:
        try:
            data, _ = sock.recvfrom(64)
            msg = data.decode().strip()
            if ":" not in msg:
                continue
            cmd, idx_str = msg.split(":", 1)
            cam_idx = int(idx_str) - 1          # 1-based → 0-based
            if not (0 <= cam_idx < len(CAMERA_IDS)):
                continue
            if cmd == "boost":
                _set_boost(cam_idx, True)
            elif cmd == "drop":
                _set_boost(cam_idx, False)
        except socket.timeout:
            pass
        except Exception as e:
            print(f"[Sender] Control parse error: {e}")


# ── Per-camera capture/send loop ───────────────────────────────────────────────
def _apply_mode(cap, w, h, fps):
    """Push new resolution+fps to an open VideoCapture."""
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  w)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
    cap.set(cv2.CAP_PROP_FPS,          fps)


def camera_loop(cam_idx: int, cam_device: int):
    port = PORTS[cam_idx]
    dest = (PC_IP, port)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 524288)

    cap = cv2.VideoCapture(cam_device, cv2.CAP_V4L2)
    if not cap.isOpened():
        cap = cv2.VideoCapture(cam_device)
    if not cap.isOpened():
        print(f"[Cam {cam_idx+1}] ERROR: cannot open device {cam_device}")
        return

    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    _apply_mode(cap, LOW_W, LOW_H, LOW_FPS)

    # Track current mode so we only re-apply when it changes
    current_high = False
    encode_params = [cv2.IMWRITE_JPEG_QUALITY, LOW_QUAL]
    frame_interval = 1.0 / LOW_FPS

    print(f"[Cam {cam_idx+1}] streaming device {cam_device} → {PC_IP}:{port}")

    while True:
        t0 = time.monotonic()

        # ── Mode switch ───────────────────────────────────────────────────────
        want_high = _is_boosted(cam_idx)
        if want_high != current_high:
            if want_high:
                _apply_mode(cap, HIGH_W, HIGH_H, HIGH_FPS)
                encode_params = [cv2.IMWRITE_JPEG_QUALITY, HIGH_QUAL]
                frame_interval = 1.0 / HIGH_FPS
            else:
                _apply_mode(cap, LOW_W, LOW_H, LOW_FPS)
                encode_params = [cv2.IMWRITE_JPEG_QUALITY, LOW_QUAL]
                frame_interval = 1.0 / LOW_FPS
                print(f"[Cam {cam_idx+1}] reverted to low-res")
            current_high = want_high
            # Flush a couple of stale frames that were buffered at the old res
            for _ in range(3):
                cap.read()

        # ── Capture + encode + send ───────────────────────────────────────────
        ret, frame = cap.read()
        if not ret:
            print(f"[Cam {cam_idx+1}] read failed, retrying…")
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
            print(f"[Cam {cam_idx+1}] send error: {e}")

        elapsed = time.monotonic() - t0
        remaining = frame_interval - elapsed
        if remaining > 0:
            time.sleep(remaining)


# ── Entry point ────────────────────────────────────────────────────────────────
def main():
    # Start control listener
    threading.Thread(target=_control_listener, daemon=True,
                     name="ControlListener").start()

    # Start one thread per camera
    for idx, dev in enumerate(CAMERA_IDS):
        t = threading.Thread(target=camera_loop, args=(idx, dev), daemon=True,
                             name=f"CamLoop-{idx+1}")
        t.start()
        time.sleep(0.1)     # stagger starts to reduce network burst at t=0

    print(f"[Sender] {len(CAMERA_IDS)} cams at {LOW_FPS}fps "
          f"({LOW_W}×{LOW_H} q={LOW_QUAL}). Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[Sender] Shutting down…")


if __name__ == "__main__":
    main()
