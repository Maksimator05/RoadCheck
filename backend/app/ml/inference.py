import logging
import time

import cv2

from app.core.config import settings
from app.ml.mock import mock_predict

logger = logging.getLogger(__name__)

# Map raw YOLO class names → canonical display types.
# D00/D10/D20 are distinct crack subtypes — keep them separate so the
# frontend can colour-code and label them correctly.
_LABEL_ALIASES: dict[str, str] = {
    # RDD2022 codes
    "d00": "longitudinal_crack",
    "d10": "transverse_crack",
    "d20": "alligator_crack",
    "d40": "pothole",
    # Verbose names (in case another model uses them)
    "longitudinal crack": "longitudinal_crack",
    "transverse crack": "transverse_crack",
    "alligator crack": "alligator_crack",
    "pothole": "pothole",
    # Generic fallbacks
    "crack": "crack",
    "patch": "patch",
    "patched": "patch",
    "rut": "rut",
    "bump": "bump",
}


class InvalidImageError(ValueError):
    """Raised when an uploaded payload cannot be decoded as an image."""


def _severity(confidence: float) -> str:
    if confidence >= 0.75:
        return "high"
    if confidence >= 0.50:
        return "medium"
    return "low"


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


def predict(image_path: str) -> dict:
    start = time.monotonic()
    image = cv2.imread(image_path)
    if image is None:
        raise InvalidImageError("The uploaded file could not be decoded as a valid image.")

    image_height, image_width = image.shape[:2]

    if settings.USE_MOCK_ML:
        defects = mock_predict(image_path)
    else:
        from app.ml.model import load_model

        model = load_model()
        predict_kwargs: dict = {
            "source": image_path,
            "conf": settings.ML_CONFIDENCE_THRESHOLD,
            "iou": settings.ML_IOU_THRESHOLD,
            "verbose": False,
        }
        if settings.ML_DEVICE.strip():
            predict_kwargs["device"] = settings.ML_DEVICE

        results = model.predict(**predict_kwargs)[0]
        defects = []
        defects = [
            d for d in defects
            if d["bbox"][1] > image_height * 0.30  # y1 должен быть ниже 30% от верха
        ]
        if results.boxes is not None:
            for box in results.boxes:
                conf = float(box.conf[0])
                cls_id = int(box.cls[0])
                raw_label = _resolve_label(results.names, cls_id)
                defects.append(
                    {
                        "type": _normalize_label(raw_label),
                        "confidence": round(conf, 4),
                        "bbox": _clip_bbox(_extract_xyxy(box), image_width, image_height),
                        "severity": _severity(conf),
                    }
                )

    processing_ms = int((time.monotonic() - start) * 1000)
    logger.info("predict() finished in %d ms; %d defect(s) found", processing_ms, len(defects))
    return {
        "defects": defects,
        "count": len(defects),
        "processing_ms": processing_ms,
        "image_width": image_width,
        "image_height": image_height,
    }