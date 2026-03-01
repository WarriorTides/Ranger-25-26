"""
cam_test.py — Run this on the Pi to find which camera indices work

Usage:
    python3 cam_test.py

It will test indices 0-10 and print which ones successfully capture a frame.
"""

import cv2
import time

INDICES_TO_TEST = list(range(11))   # tests 0 through 10

print("=" * 40)
print("CAMERA INDEX TESTER")
print("=" * 40)
print("Testing camera indices 0-10...\n")

working = []
failed = []

for idx in INDICES_TO_TEST:
    print(f"Testing index {idx}...", end=" ", flush=True)

    # Try V4L2 first (faster on Pi), fallback to default
    cap = cv2.VideoCapture(idx, cv2.CAP_V4L2)
    if not cap.isOpened():
        cap = cv2.VideoCapture(idx)

    if not cap.isOpened():
        print("✗ Could not open")
        failed.append(idx)
        continue

    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  320)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)

    # Try reading a few frames — first frame is often black/empty on Pi
    success = False
    for attempt in range(5):
        ret, frame = cap.read()
        if ret and frame is not None and frame.size > 0:
            success = True
            break
        time.sleep(0.1)

    cap.release()

    if success:
        print(f"✓ WORKS  (frame shape: {frame.shape})")
        working.append(idx)
    else:
        print("✗ Opens but no frame")
        failed.append(idx)

print("\n" + "=" * 40)
print("RESULTS")
print("=" * 40)

if working:
    print(f"Working indices: {working}")
    print(f"\nUpdate cam_sender.py:")
    print(f"  CAMERA_IDS = {working[:3]}")  # suggest first 3
else:
    print("No working cameras found!")
    print("Check: are cameras plugged in? Try 'ls /dev/video*' to list devices.")

print("=" * 40)
