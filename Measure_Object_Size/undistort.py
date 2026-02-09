import cv2
import numpy as np


img_path = '/Users/aarav/MATE/Test2.jpeg'
distorted_img = cv2.imread(img_path)
if distorted_img is None:
    raise FileNotFoundError(f"Image not found at {img_path}")


K = np.array([[1700, 0, distorted_img.shape[1] / 2],
              [0, 1700, distorted_img.shape[0] / 2],
              [0, 0, 1]], dtype=np.float32)
D = np.array([-0.4, 0.1, 0, 0], dtype=np.float32)


h, w = distorted_img.shape[:2]
new_K = cv2.fisheye.estimateNewCameraMatrixForUndistortRectify(
    K, D, (w, h), np.eye(3), balance=0.0)
map1, map2 = cv2.fisheye.initUndistortRectifyMap(
    K, D, np.eye(3), new_K, (w, h), cv2.CV_16SC2)
undistorted_img = cv2.remap(distorted_img, map1, map2,
                            interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)


output_path = '/Users/aarav/MATE/Test1600.jpeg'
cv2.imwrite(output_path, undistorted_img)
print(f"Undistorted image sabre {output_path}")
