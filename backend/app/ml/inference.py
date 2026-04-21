import logging
import time

import cv2

from app.core.config import settings
from app.ml.mock import mock_predict

logger = logging.getLogger(__name__)


def _severity(confidence: float) -> str:
    if confidence >= 0.85:
        return "high"
    if confidence >= 0.60:
        return "medium"
    return "low"


def predict(image_path: str) -> dict:
    start = time.monotonic()
    image = cv2.imread(image_path)
    image_height, image_width = image.shape[:2] if image is not None else (0, 0)

    if settings.USE_MOCK_ML:
        defects = mock_predict(image_path)
    else:
        from app.ml.model import load_model

        model = load_model()
        results = model(image_path)[0]
        defects = []
        for box in results.boxes:
            conf = float(box.conf[0])
            cls_id = int(box.cls[0])
            label = results.names[cls_id]
            x1, y1, x2, y2 = (int(v) for v in box.xyxy[0])
            defects.append(
                {
                    "type": label,
                    "confidence": round(conf, 4),
                    "bbox": [x1, y1, x2, y2],
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
