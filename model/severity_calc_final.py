import cv2
import numpy as np
import os

def calculate_severity(image_path, polygon_points):
    """
    Draws a semi-transparent red polygon overlay,
    calculates coverage percentage, and determines severity.
    """
    image = cv2.imread(image_path)
    if image is None:
        return 0, "Unknown"

    height, width, _ = image.shape
    total_area = height * width

    if not polygon_points:
        return 0, "Low"

    # Create polygon mask
    mask = np.zeros((height, width), dtype=np.uint8)
    pts = np.array(polygon_points, np.int32)
    pts = pts.reshape((-1, 1, 2))
    cv2.fillPoly(mask, [pts], 255)

    # Coverage %
    coverage_area = cv2.countNonZero(mask)
    coverage_percent = round((coverage_area / total_area) * 100, 2)

    # Severity
    if coverage_percent < 5:
        severity = "Low"
    elif coverage_percent < 20:
        severity = "Medium"
    else:
        severity = "High"

    # Transparent red overlay
    overlay = image.copy()
    cv2.fillPoly(overlay, [pts], (0, 0, 255))
    alpha = 0.4
    cv2.addWeighted(overlay, alpha, image, 1 - alpha, 0, image)

    # Save analyzed image
    base_name = os.path.basename(image_path)
    result_name = base_name.replace(".jpg", "_analyzed.jpg").replace(".png", "_analyzed.png")
    analyzed_dir = os.path.join("static_final", "analyzed_final")
    os.makedirs(analyzed_dir, exist_ok=True)
    result_path = os.path.join(analyzed_dir, result_name)
    cv2.imwrite(result_path, image)

    return coverage_percent, severity
