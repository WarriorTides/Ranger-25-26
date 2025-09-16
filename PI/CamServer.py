import cv2
import socket
import json
import base64
import time

PC_IP = "<PC_IP>"  # replace 
PORTS = [5005, 5006, 5007]  # one port per camera

sockets = [socket.socket(socket.AF_INET, socket.SOCK_DGRAM) for _ in PORTS]

caps = [cv2.VideoCapture(i) for i in range(3)]

def send_frame(cam_id, frame):
    _, buffer = cv2.imencode('.jpg', frame)
    jpg_as_text = base64.b64encode(buffer).decode('utf-8')
    msg = json.dumps({
        "type": "camera",
        "camera_id": cam_id + 1,
        "data": jpg_as_text
    }).encode()
    sockets[cam_id].sendto(msg, (PC_IP, PORTS[cam_id]))

try:
    while True:
        for i, cap in enumerate(caps):
            ret, frame = cap.read()
            if ret:
                frame = cv2.resize(frame, (320, 240)) 
                send_frame(i, frame)
        time.sleep(0.03)  
except KeyboardInterrupt:
    print("Shutting down cameras")
finally:
    for cap in caps:
        cap.release()
    for sock in sockets:
        sock.close()
