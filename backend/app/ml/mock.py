from __future__ import annotations

import math

import cv2
import numpy as np


def _clip(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _severity(confidence: float, area_ratio: float) -> str:
    if confidence >= 0.85 or area_ratio >= 0.03:
        return "high"
    if confidence >= 0.62 or area_ratio >= 0.012:
        return "medium"
    return "low"


def _python_box(x: int, y: int, w: int, h: int, width: int, height: int) -> list[int]:
    x1 = max(0, min(width - 1, int(x)))
    y1 = max(0, min(height - 1, int(y)))
    x2 = max(x1 + 1, min(width, int(x + w)))
    y2 = max(y1 + 1, min(height, int(y + h)))
    return [x1, y1, x2, y2]


def _iou(left_box: list[int], right_box: list[int]) -> float:
    x1 = max(left_box[0], right_box[0])
    y1 = max(left_box[1], right_box[1])
    x2 = min(left_box[2], right_box[2])
    y2 = min(left_box[3], right_box[3])

    if x2 <= x1 or y2 <= y1:
        return 0.0

    intersection = (x2 - x1) * (y2 - y1)
    left_area = (left_box[2] - left_box[0]) * (left_box[3] - left_box[1])
    right_area = (right_box[2] - right_box[0]) * (right_box[3] - right_box[1])
    union = left_area + right_area - intersection

    if union <= 0:
        return 0.0

    return intersection / union


def _deduplicate(defects: list[dict], overlap_threshold: float = 0.45) -> list[dict]:
    ordered = sorted(
        defects,
        key=lambda item: (
            item["type"] != "pothole",
            -item["confidence"],
            -(item["bbox"][2] - item["bbox"][0]) * (item["bbox"][3] - item["bbox"][1]),
        ),
    )
    result: list[dict] = []

    for candidate in ordered:
        if any(
            saved["type"] == candidate["type"] and _iou(saved["bbox"], candidate["bbox"]) >= overlap_threshold
            for saved in result
        ):
            continue

        result.append(candidate)

    return sorted(result, key=lambda item: (item["type"] != "pothole", -item["confidence"]))


def _detect_potholes(gray: np.ndarray) -> list[dict]:
    height, width = gray.shape
    total_area = height * width
    median_intensity = float(np.median(gray))
    blur = cv2.GaussianBlur(gray, (7, 7), 0)

    kernel_size = max(31, int(min(height, width) * 0.12))
    if kernel_size % 2 == 0:
        kernel_size += 1

    local_mean = cv2.GaussianBlur(blur, (kernel_size, kernel_size), 0)
    darkness = cv2.subtract(local_mean, blur)
    threshold = int(max(10, darkness.mean() + darkness.std() * 1.2, np.percentile(darkness, 95)))

    _, mask = cv2.threshold(darkness, threshold, 255, cv2.THRESH_BINARY)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    defects: list[dict] = []
    min_area = max(140, int(total_area * 0.00045))
    max_area = int(total_area * 0.14)

    for contour in contours:
        area = cv2.contourArea(contour)
        if area < min_area or area > max_area:
            continue

        x, y, w, h = cv2.boundingRect(contour)
        if w < 18 or h < 18:
            continue

        rect_area = w * h
        fill_ratio = area / max(1, rect_area)
        if fill_ratio < 0.22:
            continue

        perimeter = cv2.arcLength(contour, True)
        circularity = 0.0
        if perimeter > 0:
            circularity = 4 * math.pi * area / (perimeter * perimeter)
        if circularity < 0.08:
            continue

        contour_mask = np.zeros_like(gray, dtype=np.uint8)
        cv2.drawContours(contour_mask, [contour], -1, 255, thickness=-1)
        mean_darkness = cv2.mean(darkness, mask=contour_mask)[0]
        mean_intensity = cv2.mean(gray, mask=contour_mask)[0]
        if mean_darkness < 10 and mean_intensity > median_intensity * 0.78:
            continue

        area_ratio = area / total_area
        darkness_bonus = max(0.0, (median_intensity - mean_intensity) / 110)
        confidence = _clip(
            0.36 + darkness_bonus + mean_darkness / 120 + fill_ratio * 0.16 + area_ratio * 4.5,
            0.4,
            0.98,
        )
        defects.append(
            {
                "type": "pothole",
                "confidence": round(confidence, 4),
                "bbox": _python_box(x, y, w, h, width, height),
                "severity": _severity(confidence, area_ratio),
            }
        )

    return defects


def _detect_cracks(gray: np.ndarray) -> list[dict]:
    height, width = gray.shape
    total_area = height * width
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 45, 120)

    line_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 3))
    edges = cv2.dilate(edges, line_kernel, iterations=1)
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, line_kernel, iterations=1)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    defects: list[dict] = []
    min_area = max(80, int(total_area * 0.00015))
    min_length = max(42, int(max(height, width) * 0.12))

    for contour in contours:
        area = cv2.contourArea(contour)
        if area < min_area:
            continue

        x, y, w, h = cv2.boundingRect(contour)
        length = max(w, h)
        thickness = max(1, min(w, h))
        aspect_ratio = length / thickness
        fill_ratio = area / max(1, w * h)

        if length < min_length or aspect_ratio < 3.2 or fill_ratio > 0.52:
            continue

        area_ratio = area / total_area
        confidence = _clip(
            0.34 + min(0.22, aspect_ratio / 18) + min(0.2, length / max(height, width)),
            0.34,
            0.82,
        )
        defects.append(
            {
                "type": "crack",
                "confidence": round(confidence, 4),
                "bbox": _python_box(x, y, w, h, width, height),
                "severity": _severity(confidence, area_ratio),
            }
        )

    return defects


def mock_predict(image_path: str) -> list[dict]:
    image = cv2.imread(image_path)
    if image is None:
        return []

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    defects = _detect_potholes(gray) + _detect_cracks(gray)
    return _deduplicate(defects)[:10]
