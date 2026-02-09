import cv2
import socket
import json
import base64
import time
import threading

PC_IP = "192.168.1.119"
PORTS = [5005, 5006, 5007]

sockets = [socket.socket(socket.AF_INET, socket.SOCK_DGRAM) for _ in PORTS]

camera_indices = [0, 4, 3]
caps = []

for i in camera_indices:
    cap = cv2.VideoCapture(i)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
    cap.set(cv2.CAP_PROP_FPS, 15)
    caps.append(cap)
    time.sleep(0.5)

print(f"Initialized {len(caps)} cameras")


def send_frame(cam_idx, frame):
    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
    jpg_as_text = base64.b64encode(buffer).decode('utf-8')
    msg = json.dumps({
        "type": "camera",
        "camera_id": cam_idx + 1,
        "data": jpg_as_text
    }).encode()
    sockets[cam_idx].sendto(msg, (PC_IP, PORTS[cam_idx]))


def camera_loop(cam_idx, cap):
    time.sleep(cam_idx * 0.05)

    frame_count = 0
    while True:
        if not cap.isOpened():
            print(f"Camera {camera_indices[cam_idx]} not opened")
            break

        ret, frame = cap.read()
        if ret:
            send_frame(cam_idx, frame)
            frame_count += 1
            # if frame_count % 60 == 0:
            # print(
            # f"Camera {camera_indices[cam_idx]} (ID {cam_idx + 1}): {frame_count} frames sent")
        else:
            print(f"Camera {camera_indices[cam_idx]} failed to read frame")

        time.sleep(0.066)


threads = []
for idx, cap in enumerate(caps):
    t = threading.Thread(target=camera_loop, args=(idx, cap))
    t.daemon = True
    t.start()
    threads.append(t)

print("Camera streaming started... Ctrl+C =  stop ")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\nShutting down cameras...")
finally:
    for cap in caps:
        cap.release()
    for sock in sockets:
        sock.close()
    print("Cameras closed.")
