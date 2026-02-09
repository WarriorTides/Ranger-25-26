from PIL import Image
import os
import numpy as np
import cv2 as cv
from matplotlib import pyplot as plt


def preprocess_image(image_path, output_size=(256, 256), output_folder="processed_images"):
    try:
        with Image.open(image_path) as img:
            img = img.resize(output_size)
            img = img.convert("L")

            if not os.path.exists(output_folder):
                os.makedirs(output_folder)

            base_name = os.path.basename(image_path)
            output_path = os.path.join(output_folder, base_name)
            img.save(output_path)
            print(f"Processed image saved at: {output_path}")
            return output_path

    except IOError as e:
        print(f"Error processing image {image_path}: {e}")
        return None


image_path = "/Users/kashishkapoor/Ranger-25-26/Image_Rec/dataset/pic.png"
processed_path = preprocess_image(image_path, output_size=(512, 512))  # AD
if processed_path is None:
    raise Exception("Preprocessing failed")

img = cv.imread(processed_path, cv.IMREAD_GRAYSCALE)
if img is None:
    raise Exception(f"Failed to load image {processed_path}")
else:
    print(f"Image loaded successfully: {processed_path}, shape: {img.shape}")

assert img is not None, "Processed image could not be read"
blurred = cv.GaussianBlur(img, (3, 3), 0)
edges = cv.Canny(blurred, 50, 220)  # AD
plt.subplot(121), plt.imshow(img, cmap='gray')
plt.title('Preprocessed Image'), plt.xticks([]), plt.yticks([])
plt.subplot(122), plt.imshow(edges, cmap='gray')
plt.title('Edge Image'), plt.xticks([]), plt.yticks([])
plt.show()
contours, _ = cv.findContours(edges, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
min_area = 200  # AD
filtered_contours = [c for c in contours if cv.contourArea(c) > min_area]
num_crabs = len(filtered_contours)
print(f"Number of crabs detected: {num_crabs}")
