import cv2

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

