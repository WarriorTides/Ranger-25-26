import cv2
import numpy as np
import glob

TEST_IMAGE_PATH = "/Users/kashishkapoor/Ranger-25-26/Image_Rec/pic.png"
DATASET_FOLDER = "/Users/kashishkapoor/Ranger-25-26/Image_Rec/dataset/*.png"

THRESHOLD = 0.35  # -----
SCALE_STEPS = [0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.4]
RESIZE_WIDTH = 1280
WHITE_THRESH = 200


def remove_white_background(template_bgr):
    gray = cv2.cvtColor(template_bgr, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray, WHITE_THRESH, 255, cv2.THRESH_BINARY_INV)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  kernel, iterations=1)
    masked = gray.copy()
    masked[mask == 0] = 128

    return masked, mask


def match_template_masked(gray_img, template_gray, mask, threshold):
    h, w = template_gray.shape[:2]
    if w >= gray_img.shape[1] or h >= gray_img.shape[0]:
        return []

    res = cv2.matchTemplate(gray_img, template_gray, cv2.TM_CCOEFF_NORMED)
    loc = np.where(res >= threshold)

    results = []
    for pt in zip(*loc[::-1]):
        score = float(res[pt[1], pt[0]])
        results.append((int(pt[0]), int(pt[1]), int(w), int(h), score))
    return results


def orb_count_crabs(gray_img, templates_bgr, min_matches=12):
    orb = cv2.ORB_create(nfeatures=1000)
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)

    kp2, des2 = orb.detectAndCompute(gray_img, None)
    if des2 is None:
        return 0

    count = 0
    for tmpl in templates_bgr:
        if tmpl is None:
            continue
        gray_tmpl = cv2.cvtColor(tmpl, cv2.COLOR_BGR2GRAY)
        kp1, des1 = orb.detectAndCompute(gray_tmpl, None)
        if des1 is None:
            continue

        matches = bf.match(des1, des2)
        good = [m for m in matches if m.distance < 60]
        if len(good) >= min_matches:
            count += 1
            print(f"[ORB] Template matched with {len(good)} good features")

    return count


img = cv2.imread(TEST_IMAGE_PATH)
if img is None:
    print(f"Error: Could not load test image at {TEST_IMAGE_PATH}")
    exit()

scale_ratio = RESIZE_WIDTH / img.shape[1]
img = cv2.resize(img, (RESIZE_WIDTH, int(img.shape[0] * scale_ratio)))
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
gray = cv2.equalizeHist(gray)
print(f"[INFO] Test image: {img.shape[1]}x{img.shape[0]}")
template_paths = glob.glob(DATASET_FOLDER)
if not template_paths:
    print(f"Error: No templates found in {DATASET_FOLDER}")
    exit()

print(f"Found {len(template_paths)} template(s)")
templates_bgr = [cv2.imread(p) for p in template_paths]
all_boxes = []
all_scores = []

for tidx, tmpl_bgr in enumerate(templates_bgr):
    if tmpl_bgr is None:
        print(f"Template {tidx} failed to load")
        continue

    masked_tmpl, mask = remove_white_background(tmpl_bgr)
    orig_h, orig_w = masked_tmpl.shape[:2]
    best_score = 0.0

    for scale in SCALE_STEPS:
        w = int(orig_w * scale)
        h = int(orig_h * scale)

        if w < 20 or h < 20:
            continue
        if w >= gray.shape[1] or h >= gray.shape[0]:
            continue

        scaled_tmpl = cv2.resize(masked_tmpl, (w, h))
        hits = match_template_masked(gray, scaled_tmpl, mask, THRESHOLD)

        for (x, y, bw, bh, score) in hits:
            all_boxes.append([x, y, bw, bh])
            all_scores.append(score)
            if score > best_score:
                best_score = score

    print(
        f"Template {tidx} ({orig_w}x{orig_h}px) — best score: {best_score:.3f}")

print(f"Raw hits before NMS: {len(all_boxes)}")

count = 0
if all_boxes:
    indices = cv2.dnn.NMSBoxes(
        all_boxes, all_scores,
        score_threshold=THRESHOLD,
        nms_threshold=0.3
    )
    indices = indices.flatten() if len(indices) > 0 else []
    count = len(indices)

    for i in indices:
        x, y, w, h = all_boxes[i]
        cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(img, f"{all_scores[i]:.2f}", (x, y - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

if count == 0:
    print("Template matching found 0 — trying ORB feature matching...")
    count = orb_count_crabs(gray, templates_bgr)
    print(f"ORB fallback count: {count}")

print(f"\n{'='*30}")
print(f"  TOTAL CRABS DETECTEDDD!!--better be right bro: {count}")
print(f"{'='*30}\n")

cv2.putText(img, f"Crabs: {count}", (30, 70),
            cv2.FONT_HERSHEY_SIMPLEX, 2.5, (0, 255, 0), 4)
cv2.imshow("Crab Detection", img)
cv2.waitKey(0)
cv2.destroyAllWindows()
