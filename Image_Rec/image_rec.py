import cv2
import numpy as np

SIMILARITY_THRESHOLD = 20

img = cv2.imread("imaeg")

if img is None:
    print("Couldn't load it")
    exit()

output = img.copy()
img = cv2.GaussianBlur(img, (9, 9), 0)
lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
l, a, b = cv2.split(lab)
clahe = cv2.createCLAHE(
    clipLimit=3.0,
    tileGridSize=(8, 8)
)

l = clahe.apply(l)
lab = cv2.merge((l, a, b))
img = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
scene_h = np.mean(hsv[:, :, 0])
scene_s = np.mean(hsv[:, :, 1])
scene_v = np.mean(hsv[:, :, 2])
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
edges = cv2.Canny(gray, 40, 120)
kernel = np.ones((7, 7), np.uint8)
edges = cv2.dilate(edges, kernel, iterations=1)
edges = cv2.morphologyEx(
    edges,
    cv2.MORPH_CLOSE,
    kernel
)

contours, _ = cv2.findContours(
    edges,
    cv2.RETR_EXTERNAL,
    cv2.CHAIN_APPROX_SIMPLE
)

objects = []

image_area = img.shape[0] * img.shape[1]

for cnt in contours:
    area = cv2.contourArea(cnt)
    if area < image_area * 0.0005:
        continue
    hull = cv2.convexHull(cnt)
    hull_area = cv2.contourArea(hull)
    if hull_area == 0:
        continue
    solidity = area / hull_area
    if solidity < 0.35:
        continue
    x, y, w, h = cv2.boundingRect(cnt)
    object_mask = np.zeros(
        gray.shape,
        dtype=np.uint8
    )

    cv2.drawContours(
        object_mask,
        [cnt],
        -1,
        255,
        -1
    )

    mean_h = cv2.mean(
        hsv[:, :, 0],
        mask=object_mask
    )[0]

    mean_s = cv2.mean(
        hsv[:, :, 1],
        mask=object_mask
    )[0]

    mean_v = cv2.mean(
        hsv[:, :, 2],
        mask=object_mask
    )[0]

    relative_darkness = scene_v - mean_v
    relative_coolness = mean_h - scene_h
    relative_saturation = mean_s - scene_s

    score = (
        relative_darkness * 1.5 +
        relative_coolness * 1.0 +
        relative_saturation * 0.3
    )

    objects.append({
        "box": (x, y, w, h),
        "score": score
    })

if len(objects) == 0:
    print("No objects found")
    exit()

objects.sort(
    key=lambda o: o["score"],
    reverse=True
)

reference_score = objects[0]["score"]
green_crabs = []
for obj in objects:

    difference = abs(
        obj["score"] - reference_score
    )

    if difference < SIMILARITY_THRESHOLD:
        green_crabs.append(obj)

for crab in green_crabs:
    x, y, w, h = crab["box"]

    cv2.rectangle(
        output,
        (x, y),
        (x + w, y + h),
        (0, 255, 0),
        3
    )

cv2.putText(
    output,
    f"European Green Crabs: {len(green_crabs)}",
    (20, 50),
    cv2.FONT_HERSHEY_SIMPLEX,
    1,
    (0, 255, 0),
    3
)

cv2.imshow("Edges", edges)
cv2.imshow("Detection", output)
cv2.waitKey(0)
cv2.destroyAllWindows()
