import cv2
import numpy as np

img = cv2.imread("input.jpg")

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

cv2.imwrite("undistorted.jpg", undistorted)
