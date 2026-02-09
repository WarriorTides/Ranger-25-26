import cv2
<<<<<<< HEAD
import os
import subprocess

def list_arducam_devices():
    devices = {}
    try:
        result = subprocess.run(["v4l2-ctl", "--list-devices"], capture_output=True, text=True)
        lines = result.stdout.splitlines()
        
        current_cam = None
        for line in lines:
            if line.strip() == "":
                continue
            if not line.startswith("\t"):
                current_cam = line.strip()
                devices[current_cam] = []
            else:
                dev_path = line.strip()
                if dev_path.startswith("/dev/video") and "Arducam" in current_cam:
                    devices[current_cam].append(dev_path)
    except FileNotFoundError:
        print("v4l2-ctl not found. Install it with: sudo apt install v4l-utils")
    return devices

def test_camera(dev):
    cap = cv2.VideoCapture(dev)
    if cap.isOpened():
        ret, frame = cap.read()
        cap.release()
        if ret:
            return True
        else:
            return False
    else:
        return False

def main():
    print("Detecting Arducam devicesss")
    cameras = list_arducam_devices()
    
    if not cameras:
        print("No Arducam cameras found")
        return
    
    for cam_name, nodes in cameras.items():
        print(f"\nCamera: {cam_name}")
        for dev in nodes:
            works = test_camera(dev)
            status = "WORKS!" if works else "FAILED"
            print(f"  {dev}: {status}")

    print("\nStreaming first working node of each camera. Press 'q' to quit.")
    caps = []
    for cam_name, nodes in cameras.items():
        for dev in nodes:
            if test_camera(dev):
                cap = cv2.VideoCapture(dev)
                if cap.isOpened():
                    caps.append((cam_name, cap))
                break 
    
    if not caps:
        print("No cameras available for streaming.")
        return

    while True:
        for cam_name, cap in caps:
            ret, frame = cap.read()
            if ret:
                cv2.imshow(cam_name, frame)
            else:
                print(f"{cam_name}: Failed to read frame")
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    for _, cap in caps:
        cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
=======

for i in range(10):
    print(f"\nTrying camera {i}...")
    cap = cv2.VideoCapture(i)

    if cap.isOpened():
        ret, frame = cap.read()
        if ret and frame is not None:
            print(f"Camera {i} works: {frame.shape[1]}x{frame.shape[0]}")
        else:
            print(f"Camera {i} opened but can't read frames")
        cap.release()
    else:
        print(f"Camera {i} won't open")

>>>>>>> 8847c960a9c8050c2d558a2b7e65d68712b5d4d4
