import cv2
import numpy as np

print("Starting program...")

img = cv2.imread("input.jpg")

if img is None:
    raise FileNotFoundError("Could not load image")

K = np.load("K.npy")
D = np.load("D.npy")

h, w = img.shape[:2]

new_K = cv2.fisheye.estimateNewCameraMatrixForUndistortRectify(
    K,
    D,
    (w, h),
    np.eye(3),
    balance=0.0
)

map1, map2 = cv2.fisheye.initUndistortRectifyMap(
    K,
    D,
    np.eye(3),
    new_K,
    (w, h),
    cv2.CV_16SC2
)

undistorted = cv2.remap(
    img,
    map1,
    map2,
    interpolation=cv2.INTER_LINEAR,
    borderMode=cv2.BORDER_CONSTANT
)

points = []

display_img = undistorted.copy()


def click_event(event, x, y, flags, param):

    global points, display_img

    if event == cv2.EVENT_LBUTTONDOWN:

        points.append((x, y))

        cv2.circle(display_img, (x, y), 5, (0, 0, 255), -1)

        cv2.imshow("Select 4 Corners", display_img)

        print(f"Point {len(points)}: ({x}, {y})")

        if len(points) == 4:

            pts1 = np.float32(points)

            width = max(
                np.linalg.norm(pts1[0] - pts1[1]),
                np.linalg.norm(pts1[2] - pts1[3])
            )

            height = max(
                np.linalg.norm(pts1[0] - pts1[3]),
                np.linalg.norm(pts1[1] - pts1[2])
            )

            pts2 = np.float32([
                [0, 0],
                [width, 0],
                [width, height],
                [0, height]
            ])

            matrix = cv2.getPerspectiveTransform(pts1, pts2)

            result = cv2.warpPerspective(
                undistorted,
                matrix,
                (int(width), int(height))
            )

            cv2.imshow("Flattened Image", result)

            cv2.imwrite("flattened.jpg", result)

            print("Saved flattened.jpg")


print("\nClick points in this order:")
print("1. Top-left")
print("2. Top-right")
print("3. Bottom-right")
print("4. Bottom-left")

cv2.imshow("Select 4 Corners", display_img)

cv2.setMouseCallback(
    "Select 4 Corners",
    click_event
)

cv2.waitKey(0)
cv2.destroyAllWindows()