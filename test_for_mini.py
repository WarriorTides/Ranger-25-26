import cv2
import glob

video_nodes = glob.glob("/dev/video*")
working_cams = []

for node in video_nodes:
    print(f"Checking {node}...")

    cap = cv2.VideoCapture(node, cv2.CAP_V4L2)

    if not cap.isOpened():
        cap.release()
        continue

    success = cap.grab()

    if success:
        ret, frame = cap.retrieve()
        if ret:
            print(f"{node} works!!!!")
            working_cams.append(node)
    else:
        print(f"{node} grab failed (likely bad node)")

    cap.release()

print("Use these nodes:", working_cams)