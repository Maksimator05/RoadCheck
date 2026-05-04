from __future__ import annotations

import logging
import time
from typing import Any

import cv2
import numpy as np

from app.core.config import settings
from app.ml.mock import mock_predict

logger = logging.getLogger(__name__)

# Map raw YOLO class names to canonical API values used by the frontend.
_LABEL_ALIASES: dict[str, str] = {
    "d00": "longitudinal_crack",
    "d10": "transverse_crack",
    "d20": "alligator_crack",
    "d40": "pothole",
    "longitudinal crack": "longitudinal_crack",
    "transverse crack": "transverse_crack",
    "alligator crack": "alligator_crack",
    "pothole": "pothole",
    "crack": "crack",
    "patch": "patch",
    "patched": "patch",
    "rut": "rut",
    "bump": "bump",
}

_CRACK_TYPES = {"crack", "longitudinal_crack", "transverse_crack", "alligator_crack"}
_POTHOLE_TYPES = {"pothole"}

_MIN_BBOX_AREA_RATIO = 0.0005
_MAX_BBOX_AREA_RATIO = 0.60
_TOP_ZONE_CUTOFF_RATIO = 0.18
_ROAD_MASK_TOP_RATIO = 0.24
_TREE_GREEN_RATIO_THRESHOLD = 0.18
_TILE_WIDTH_RATIO = 0.52
_TILE_HEIGHT_RATIO = 0.62
_MIN_TILE_SIZE = 192


class InvalidImageError(ValueError):
    """Raised when an uploaded payload cannot be decoded as an image."""


def _severity(confidence: float) -> str:
    if confidence >= 0.75:
        return "high"
    if confidence >= 0.50:
        return "medium"
    return "low"


def _odd(value: int) -> int:
    return value if value % 2 else value + 1


def _damage_family(label: str) -> str:
    if label in _POTHOLE_TYPES:
        return "pothole"
    if label in _CRACK_TYPES:
        return "crack"
    return label


def _normalize_label(label: str) -> str:
    normalized = " ".join(label.strip().lower().replace("_", " ").replace("-", " ").split())
    if not normalized:
        return "unknown"
    return _LABEL_ALIASES.get(normalized, normalized.replace(" ", "_"))


def _clip_bbox(values: list[float], width: int, height: int) -> list[int]:
    x1 = max(0, min(width - 1, int(values[0])))
    y1 = max(0, min(height - 1, int(values[1])))
    x2 = max(x1 + 1, min(width, int(values[2])))
    y2 = max(y1 + 1, min(height, int(values[3])))
    return [x1, y1, x2, y2]


def _extract_xyxy(box) -> list[float]:
    coords = box.xyxy[0]
    if hasattr(coords, "tolist"):
        return coords.tolist()
    return list(coords)


def _resolve_label(names, cls_id: int) -> str:
    if isinstance(names, dict):
        return str(names.get(cls_id, cls_id))
    if isinstance(names, list) and 0 <= cls_id < len(names):
        return str(names[cls_id])
    return str(cls_id)


def _bbox_area(bbox: list[int]) -> int:
    return max(1, (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]))


def _bbox_intersection_area(first: list[int], second: list[int]) -> int:
    x1 = max(first[0], second[0])
    y1 = max(first[1], second[1])
    x2 = min(first[2], second[2])
    y2 = min(first[3], second[3])
    if x2 <= x1 or y2 <= y1:
        return 0
    return (x2 - x1) * (y2 - y1)


def _bbox_iou(first: list[int], second: list[int]) -> float:
    intersection = _bbox_intersection_area(first, second)
    if intersection <= 0:
        return 0.0
    union = _bbox_area(first) + _bbox_area(second) - intersection
    return intersection / float(max(1, union))


def _bbox_containment(first: list[int], second: list[int]) -> tuple[float, float]:
    intersection = _bbox_intersection_area(first, second)
    if intersection <= 0:
        return 0.0, 0.0

    first_area = _bbox_area(first)
    second_area = _bbox_area(second)
    containment = intersection / float(max(1, min(first_area, second_area)))
    area_ratio = min(first_area, second_area) / float(max(first_area, second_area))
    return containment, area_ratio


def _confidence_threshold_for_label(label: str) -> float:
    family = _damage_family(label)
    if family == "pothole":
        return float(settings.ML_POTHOLE_CONFIDENCE_THRESHOLD)
    if family == "crack":
        return float(settings.ML_CRACK_CONFIDENCE_THRESHOLD)
    return float(settings.ML_CONFIDENCE_THRESHOLD)


def _prediction_confidence_floor() -> float:
    threshold_values = [
        float(settings.ML_CONFIDENCE_THRESHOLD),
        float(settings.ML_POTHOLE_CONFIDENCE_THRESHOLD),
        float(settings.ML_CRACK_CONFIDENCE_THRESHOLD),
    ]
    return float(np.clip(min(threshold_values), 0.01, 0.95))


def _build_perspective_road_mask(width: int, height: int) -> np.ndarray:
    mask = np.zeros((height, width), dtype=np.uint8)
    polygon = np.array(
        [
            [int(width * 0.02), height - 1],
            [int(width * 0.98), height - 1],
            [int(width * 0.70), int(height * 0.34)],
            [int(width * 0.30), int(height * 0.34)],
        ],
        dtype=np.int32,
    )
    cv2.fillConvexPoly(mask, polygon, 255)
    return mask


def _build_road_mask(image: np.ndarray) -> np.ndarray:
    height, width = image.shape[:2]
    image_area = height * width
    fallback_mask = _build_perspective_road_mask(width, height)

    seed_x1 = int(width * 0.35)
    seed_x2 = int(width * 0.65)
    seed_y1 = int(height * 0.78)
    seed_y2 = int(height * 0.98)
    if seed_x2 <= seed_x1 or seed_y2 <= seed_y1:
        return fallback_mask

    hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    lab_image = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)

    seed_lab = lab_image[seed_y1:seed_y2, seed_x1:seed_x2].reshape(-1, 3).astype(np.float32)
    seed_sat = hsv_image[seed_y1:seed_y2, seed_x1:seed_x2, 1].reshape(-1).astype(np.float32)
    seed_val = hsv_image[seed_y1:seed_y2, seed_x1:seed_x2, 2].reshape(-1).astype(np.float32)
    if seed_lab.size == 0:
        return fallback_mask

    road_lab = np.median(seed_lab, axis=0)
    color_distance = np.linalg.norm(lab_image.astype(np.float32) - road_lab, axis=2)
    seed_distance = color_distance[seed_y1:seed_y2, seed_x1:seed_x2]

    distance_threshold = float(np.clip(np.percentile(seed_distance, 95) + 12.0, 18.0, 46.0))
    saturation_threshold = float(np.clip(np.percentile(seed_sat, 90) + 30.0, 55.0, 160.0))
    value_median = float(np.median(seed_val))

    candidate_mask = (
        (color_distance <= distance_threshold)
        & (hsv_image[:, :, 1].astype(np.float32) <= saturation_threshold)
    )
    dark_road_mask = (
        (color_distance <= distance_threshold * 1.35)
        & (hsv_image[:, :, 2].astype(np.float32) <= value_median + 18.0)
    )
    candidate_mask = np.logical_or(candidate_mask, dark_road_mask).astype(np.uint8) * 255
    candidate_mask[: int(height * _ROAD_MASK_TOP_RATIO), :] = 0

    close_kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE,
        (_odd(max(9, min(width, height) // 28)), _odd(max(9, min(width, height) // 28))),
    )
    open_kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE,
        (_odd(max(5, min(width, height) // 72)), _odd(max(5, min(width, height) // 72))),
    )
    candidate_mask = cv2.morphologyEx(candidate_mask, cv2.MORPH_CLOSE, close_kernel, iterations=1)
    candidate_mask = cv2.morphologyEx(candidate_mask, cv2.MORPH_OPEN, open_kernel, iterations=1)

    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(candidate_mask, connectivity=8)
    road_mask = np.zeros_like(candidate_mask)
    bottom_seed = (
        slice(int(height * 0.82), height),
        slice(int(width * 0.22), int(width * 0.78)),
    )

    for label_id in range(1, num_labels):
        if stats[label_id, cv2.CC_STAT_AREA] < image_area * 0.03:
            continue
        component = labels == label_id
        if not component[bottom_seed].any():
            continue
        road_mask[component] = 255

    if cv2.countNonZero(road_mask) < image_area * 0.08:
        return fallback_mask

    combined_mask = cv2.bitwise_and(road_mask, fallback_mask)
    if cv2.countNonZero(combined_mask) < image_area * 0.05:
        combined_mask = road_mask

    combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, close_kernel, iterations=1)
    return combined_mask


def _road_overlap_ratio(road_mask: np.ndarray, bbox: list[int]) -> float:
    x1, y1, x2, y2 = bbox
    crop = road_mask[y1:y2, x1:x2]
    if crop.size == 0:
        return 0.0
    return cv2.countNonZero(crop) / float(crop.size)


def _bbox_center_on_road(road_mask: np.ndarray, bbox: list[int]) -> bool:
    x1, y1, x2, y2 = bbox
    cx = max(0, min(road_mask.shape[1] - 1, int((x1 + x2) / 2)))
    cy = max(0, min(road_mask.shape[0] - 1, int((y1 + y2) / 2)))
    return bool(road_mask[cy, cx] > 0)


def _vegetation_ratio(hsv_image: np.ndarray, bbox: list[int]) -> float:
    x1, y1, x2, y2 = bbox
    crop = hsv_image[y1:y2, x1:x2]
    if crop.size == 0:
        return 0.0

    hue = crop[:, :, 0]
    saturation = crop[:, :, 1]
    value = crop[:, :, 2]
    green_mask = (hue >= 35) & (hue <= 95) & (saturation >= 50) & (value >= 35)
    return float(green_mask.mean())


def _tighten_bbox_to_road(bbox: list[int], road_mask: np.ndarray) -> list[int]:
    x1, y1, x2, y2 = bbox
    crop = road_mask[y1:y2, x1:x2]
    ys, xs = np.where(crop > 0)
    if xs.size == 0 or ys.size == 0:
        return bbox

    padding = max(4, min(x2 - x1, y2 - y1) // 14)
    tightened = [
        max(x1, x1 + int(xs.min()) - padding),
        max(y1, y1 + int(ys.min()) - padding),
        min(x2, x1 + int(xs.max()) + padding + 1),
        min(y2, y1 + int(ys.max()) + padding + 1),
    ]

    original_area = max(1, (x2 - x1) * (y2 - y1))
    tightened_area = max(1, (tightened[2] - tightened[0]) * (tightened[3] - tightened[1]))
    if tightened_area < original_area * 0.20:
        return bbox

    return tightened


def _is_valid_detection(
    bbox: list[int],
    image_width: int,
    image_height: int,
    label: str,
    road_mask: np.ndarray,
    hsv_image: np.ndarray,
) -> bool:
    x1, y1, x2, y2 = bbox
    image_area = image_width * image_height
    bbox_w = x2 - x1
    bbox_h = y2 - y1
    bbox_area = bbox_w * bbox_h
    area_ratio = bbox_area / image_area if image_area > 0 else 0.0
    cy_ratio = ((y1 + y2) / 2) / image_height if image_height > 0 else 0.0
    road_overlap = _road_overlap_ratio(road_mask, bbox)
    center_on_road = _bbox_center_on_road(road_mask, bbox)
    green_ratio = _vegetation_ratio(hsv_image, bbox)
    family = _damage_family(label)

    if cy_ratio < _TOP_ZONE_CUTOFF_RATIO:
        return False
    if area_ratio < _MIN_BBOX_AREA_RATIO or area_ratio > _MAX_BBOX_AREA_RATIO:
        return False
    if green_ratio >= _TREE_GREEN_RATIO_THRESHOLD and road_overlap < 0.45:
        return False

    min_overlap = 0.32 if family == "pothole" else 0.18
    if road_overlap < min_overlap and not center_on_road:
        return False

    aspect_ratio = bbox_h / max(1, bbox_w)
    if family != "crack" and aspect_ratio > 2.6 and road_overlap < 0.65:
        return False

    return True


def _sliding_positions(start: int, end: int, window_size: int, overlap: float) -> list[int]:
    length = max(0, end - start)
    if length <= 0:
        return [start]

    window_size = max(1, min(window_size, length))
    if window_size == length:
        return [start]

    stride = max(1, int(round(window_size * (1.0 - overlap))))
    last_start = end - window_size
    positions = [start]
    cursor = start

    while cursor < last_start:
        next_cursor = min(last_start, cursor + stride)
        if next_cursor <= positions[-1]:
            break
        positions.append(next_cursor)
        cursor = next_cursor

    return positions


def _build_lower_road_tiles(image: np.ndarray, road_mask: np.ndarray) -> list[tuple[int, int, int, int]]:
    height, width = image.shape[:2]
    overlap = float(np.clip(settings.ML_TILE_OVERLAP, 0.05, 0.80))
    roi_top_ratio = float(np.clip(settings.ML_TILE_ROI_TOP_RATIO, _TOP_ZONE_CUTOFF_RATIO, 0.75))
    min_road_coverage = float(np.clip(settings.ML_TILE_MIN_ROAD_COVERAGE, 0.01, 0.90))

    roi_top = int(height * roi_top_ratio)
    roi_height = max(1, height - roi_top)
    tile_width = min(width, max(_MIN_TILE_SIZE, int(round(width * _TILE_WIDTH_RATIO))))
    tile_height = min(roi_height, max(_MIN_TILE_SIZE, int(round(roi_height * _TILE_HEIGHT_RATIO))))

    x_positions = _sliding_positions(0, width, tile_width, overlap)
    y_positions = _sliding_positions(roi_top, height, tile_height, overlap)

    tiles: list[tuple[int, int, int, int]] = []
    seen: set[tuple[int, int, int, int]] = set()

    for y1 in y_positions:
        y2 = min(height, y1 + tile_height)
        for x1 in x_positions:
            x2 = min(width, x1 + tile_width)
            tile = (x1, y1, x2, y2)
            if tile in seen:
                continue

            road_coverage = _road_overlap_ratio(road_mask, [x1, y1, x2, y2])
            if road_coverage < min_road_coverage:
                continue

            seen.add(tile)
            tiles.append(tile)

    return tiles


def _iter_inference_sources(
    image_path: str,
    image: np.ndarray,
    road_mask: np.ndarray,
) -> list[tuple[object, int, int, bool]]:
    sources: list[tuple[object, int, int, bool]] = [(image_path, 0, 0, False)]
    for x1, y1, x2, y2 in _build_lower_road_tiles(image, road_mask):
        sources.append((image[y1:y2, x1:x2].copy(), x1, y1, True))
    return sources


def _predict_real_model(source: object):
    from app.ml.model import load_model

    model = load_model()
    predict_kwargs: dict[str, object] = {
        "source": source,
        "conf": _prediction_confidence_floor(),
        "iou": settings.ML_IOU_THRESHOLD,
        "verbose": False,
    }

    device = settings.ML_DEVICE.strip()
    if device:
        predict_kwargs["device"] = device

    try:
        return model.predict(**predict_kwargs)[0]
    except Exception as exc:
        if device and device.lower() != "cpu":
            logger.warning("ML inference failed on device '%s', retrying on CPU: %s", device, exc)
            predict_kwargs["device"] = "cpu"
            return model.predict(**predict_kwargs)[0]
        raise


def _collect_detection_candidates(
    image_path: str,
    image: np.ndarray,
    road_mask: np.ndarray,
    hsv_image: np.ndarray,
) -> list[dict[str, Any]]:
    image_height, image_width = image.shape[:2]
    candidates: list[dict[str, Any]] = []

    for source, offset_x, offset_y, is_tile in _iter_inference_sources(image_path, image, road_mask):
        results = _predict_real_model(source)
        if results.boxes is None:
            continue

        result_names = getattr(results, "names", {})
        for box in results.boxes:
            conf = float(box.conf[0])
            cls_id = int(box.cls[0])
            raw_label = _resolve_label(result_names, cls_id)
            normalized_label = _normalize_label(raw_label)

            if conf < _confidence_threshold_for_label(normalized_label):
                continue

            local_bbox = _extract_xyxy(box)
            global_bbox = _clip_bbox(
                [
                    local_bbox[0] + offset_x,
                    local_bbox[1] + offset_y,
                    local_bbox[2] + offset_x,
                    local_bbox[3] + offset_y,
                ],
                image_width,
                image_height,
            )

            if not _is_valid_detection(
                global_bbox,
                image_width,
                image_height,
                normalized_label,
                road_mask,
                hsv_image,
            ):
                continue

            refined_bbox = _tighten_bbox_to_road(global_bbox, road_mask)
            candidates.append(
                {
                    "type": normalized_label,
                    "confidence": conf,
                    "bbox": refined_bbox,
                    "severity": _severity(conf),
                    "_family": _damage_family(normalized_label),
                    "_is_tile": is_tile,
                }
            )

    return candidates


def _should_suppress_detection(candidate: dict[str, Any], kept: dict[str, Any]) -> bool:
    if candidate["_family"] != kept["_family"]:
        return False

    bbox_a = candidate["bbox"]
    bbox_b = kept["bbox"]
    iou = _bbox_iou(bbox_a, bbox_b)
    if iou >= float(settings.ML_TILE_NMS_IOU_THRESHOLD):
        return True

    containment, area_ratio = _bbox_containment(bbox_a, bbox_b)
    return containment >= 0.85 and area_ratio >= 0.28


def _merge_detections_with_nms(detections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sorted_detections = sorted(
        detections,
        key=lambda item: (
            item["confidence"],
            1 if item["_is_tile"] else 0,
            -_bbox_area(item["bbox"]),
        ),
        reverse=True,
    )

    kept: list[dict[str, Any]] = []
    for detection in sorted_detections:
        if any(_should_suppress_detection(detection, current) for current in kept):
            continue
        kept.append(detection)

    merged = []
    for item in sorted(kept, key=lambda current: (current["bbox"][1], current["bbox"][0])):
        merged.append(
            {
                "type": item["type"],
                "confidence": round(float(item["confidence"]), 4),
                "bbox": item["bbox"],
                "severity": item["severity"],
            }
        )
    return merged


def predict(image_path: str) -> dict:
    start = time.monotonic()
    image = cv2.imread(image_path)
    if image is None:
        raise InvalidImageError("The uploaded file could not be decoded as a valid image.")

    image_height, image_width = image.shape[:2]

    if settings.USE_MOCK_ML:
        defects = mock_predict(image_path)
    else:
        hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        road_mask = _build_road_mask(image)
        candidates = _collect_detection_candidates(image_path, image, road_mask, hsv_image)
        defects = _merge_detections_with_nms(candidates)

    processing_ms = int((time.monotonic() - start) * 1000)
    logger.info("predict() finished in %d ms; %d defect(s) found", processing_ms, len(defects))
    return {
        "defects": defects,
        "count": len(defects),
        "processing_ms": processing_ms,
        "image_width": image_width,
        "image_height": image_height,
    }
