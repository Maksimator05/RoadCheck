import cv2
import numpy as np

from app.ml.inference import (
    _build_lower_road_tiles,
    _build_road_mask,
    _confidence_threshold_for_label,
    _is_valid_detection,
    _merge_detections_with_nms,
    _tighten_bbox_to_road,
)


def _synthetic_scene() -> np.ndarray:
    image = np.full((360, 640, 3), 225, dtype=np.uint8)
    road_polygon = np.array([[24, 359], [616, 359], [430, 120], [210, 120]], dtype=np.int32)
    cv2.fillConvexPoly(image, road_polygon, (96, 96, 96))

    # Trees and foliage outside the road area.
    cv2.rectangle(image, (0, 30), (185, 250), (40, 120, 40), thickness=-1)
    cv2.rectangle(image, (458, 10), (639, 220), (35, 110, 35), thickness=-1)

    # Road damage region.
    cv2.circle(image, (320, 255), 38, (24, 24, 24), thickness=-1)
    return image


def test_build_road_mask_prefers_bottom_central_road():
    image = _synthetic_scene()
    road_mask = _build_road_mask(image)

    assert road_mask[300, 320] > 0
    assert road_mask[120, 80] == 0


def test_detection_filter_rejects_tree_bbox_and_keeps_road_bbox():
    image = _synthetic_scene()
    road_mask = _build_road_mask(image)
    hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    image_height, image_width = image.shape[:2]

    assert not _is_valid_detection([20, 40, 180, 230], image_width, image_height, "pothole", road_mask, hsv_image)
    assert _is_valid_detection([250, 200, 390, 320], image_width, image_height, "pothole", road_mask, hsv_image)


def test_tighten_bbox_to_road_reduces_side_spill():
    image = _synthetic_scene()
    road_mask = _build_road_mask(image)
    bbox = [40, 90, 360, 340]

    tightened = _tighten_bbox_to_road(bbox, road_mask)

    original_area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
    tightened_area = (tightened[2] - tightened[0]) * (tightened[3] - tightened[1])

    assert tightened[0] >= bbox[0]
    assert tightened[1] >= bbox[1]
    assert tightened[2] <= bbox[2]
    assert tightened[3] <= bbox[3]
    assert tightened_area <= original_area


def test_build_lower_road_tiles_stays_in_bottom_road_roi(monkeypatch):
    image = _synthetic_scene()
    road_mask = _build_road_mask(image)

    monkeypatch.setattr("app.ml.inference.settings.ML_TILE_OVERLAP", 0.35)
    monkeypatch.setattr("app.ml.inference.settings.ML_TILE_ROI_TOP_RATIO", 0.28)
    monkeypatch.setattr("app.ml.inference.settings.ML_TILE_MIN_ROAD_COVERAGE", 0.16)

    tiles = _build_lower_road_tiles(image, road_mask)

    assert len(tiles) >= 2
    assert all(tile[1] >= int(image.shape[0] * 0.28) for tile in tiles)
    assert all(tile[3] <= image.shape[0] for tile in tiles)


def test_merge_detections_with_nms_merges_tile_duplicates():
    detections = [
        {
            "type": "pothole",
            "confidence": 0.61,
            "bbox": [220, 180, 340, 280],
            "severity": "medium",
            "_family": "pothole",
            "_is_tile": False,
        },
        {
            "type": "pothole",
            "confidence": 0.58,
            "bbox": [228, 186, 334, 274],
            "severity": "medium",
            "_family": "pothole",
            "_is_tile": True,
        },
        {
            "type": "pothole",
            "confidence": 0.56,
            "bbox": [390, 185, 465, 265],
            "severity": "medium",
            "_family": "pothole",
            "_is_tile": True,
        },
    ]

    merged = _merge_detections_with_nms(detections)

    assert len(merged) == 2
    assert merged[0]["bbox"] == [220, 180, 340, 280]
    assert merged[1]["bbox"] == [390, 185, 465, 265]


def test_confidence_thresholds_are_lower_for_cracks_than_potholes(monkeypatch):
    monkeypatch.setattr("app.ml.inference.settings.ML_CONFIDENCE_THRESHOLD", 0.22)
    monkeypatch.setattr("app.ml.inference.settings.ML_POTHOLE_CONFIDENCE_THRESHOLD", 0.48)
    monkeypatch.setattr("app.ml.inference.settings.ML_CRACK_CONFIDENCE_THRESHOLD", 0.24)

    assert _confidence_threshold_for_label("pothole") == 0.48
    assert _confidence_threshold_for_label("longitudinal_crack") == 0.24
    assert _confidence_threshold_for_label("patch") == 0.22
