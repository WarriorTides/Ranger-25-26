import cv2
import glob

video_nodes = glob.glob("/dev/video*")
working_cams = []

for node in video_nodes:
    cap = cv2.VideoCapture(node)
    ret, frame = cap.read()
    if ret:
        print(f"{node} works!")
        working_cams.append(node)
    cap.release()

print("Use these nodes:", working_cams)
