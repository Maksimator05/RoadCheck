from __future__ import annotations

from pathlib import Path
from typing import Any

from app.core.config import BASE_DIR, settings

_model = None


class ModelConfigurationError(RuntimeError):
    """Raised when the real ML backend is configured incorrectly."""


class ModelLoadError(RuntimeError):
    """Raised when YOLO weights cannot be loaded."""


def resolve_model_path() -> Path:
    model_path = Path(settings.ML_MODEL_PATH)
    if not model_path.is_absolute():
        model_path = BASE_DIR / model_path
    return model_path.resolve()


def get_model_status() -> dict[str, Any]:
    model_path = resolve_model_path()
    use_mock = settings.USE_MOCK_ML
    return {
        "mode": "mock" if use_mock else "yolo",
        "backend": "opencv-mock" if use_mock else "ultralytics",
        "ready": use_mock or model_path.exists(),
        "loaded": _model is not None,
        "model_path": str(model_path),
    }


def warmup_model() -> None:
    if settings.USE_MOCK_ML or not settings.ML_LOAD_ON_STARTUP:
        return
    load_model()


def load_model():
    global _model

    model_path = resolve_model_path()
    if not model_path.exists():
        raise ModelConfigurationError(
            "YOLO weights were not found. Put a model file at "
            f"'{model_path}' or update ML_MODEL_PATH."
        )

    if _model is None:
        try:
            from ultralytics import YOLO
        except ImportError as exc:  # pragma: no cover - depends on local environment
            raise ModelLoadError(
                "Ultralytics is not installed. Install backend requirements before enabling real ML."
            ) from exc

        try:
            _model = YOLO(str(model_path))
        except Exception as exc:  # pragma: no cover - depends on local weights/runtime
            raise ModelLoadError(f"Failed to load YOLO model from '{model_path}': {exc}") from exc

    return _model
