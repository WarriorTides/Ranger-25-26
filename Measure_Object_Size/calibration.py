import cv2
import numpy as np
import glob

CHECKERBOARD = (6, 4)

objp = np.zeros((1, CHECKERBOARD[0]*CHECKERBOARD[1], 3), np.float32)
objp[0, :, :2] = np.mgrid[0:CHECKERBOARD[0],
                          0:CHECKERBOARD[1]].T.reshape(-1, 2)

objpoints = []
imgpoints = []

images = glob.glob('calibration_images/*.jpg')

for fname in images:

    img = cv2.imread(fname)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    ret, corners = cv2.findChessboardCorners(
        gray,
        CHECKERBOARD,
        cv2.CALIB_CB_ADAPTIVE_THRESH
        + cv2.CALIB_CB_FAST_CHECK
        + cv2.CALIB_CB_NORMALIZE_IMAGE
    )

    if ret:

        corners2 = cv2.cornerSubPix(
            gray,
            corners,
            (11, 11),
            (-1, -1),
            (
                cv2.TERM_CRITERIA_EPS +
                cv2.TERM_CRITERIA_MAX_ITER,
                30,
                0.001
            )
        )

        objpoints.append(objp)
        imgpoints.append(corners2)

        cv2.drawChessboardCorners(
            img,
            CHECKERBOARD,
            corners2,
            ret
        )

        cv2.imshow('img', img)
        cv2.waitKey(200)

cv2.destroyAllWindows()

K = np.zeros((3, 3))
D = np.zeros((4, 1))

rvecs = [np.zeros((1, 1, 3), dtype=np.float64)
         for i in range(len(objpoints))]

tvecs = [np.zeros((1, 1, 3), dtype=np.float64)
         for i in range(len(objpoints))]

rms, _, _, _, _ = cv2.fisheye.calibrate(
    objpoints,
    imgpoints,
    gray.shape[::-1],
    K,
    D,
    rvecs,
    tvecs,
    cv2.fisheye.CALIB_RECOMPUTE_EXTRINSIC,
    (
        cv2.TERM_CRITERIA_EPS +
        cv2.TERM_CRITERIA_MAX_ITER,
        100,
        1e-6
    )
)

np.save("K.npy", K)
np.save("D.npy", D)

print("RMS ERROR:", rms)
print("K:")
print(K)
print("D:")
print(D)
