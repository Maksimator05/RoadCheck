from pathlib import Path

_model = None


def load_model():
    global _model
    if _model is None:
        from ultralytics import YOLO
        weights_path = Path(__file__).parent / "weights" / "best.pt"
        _model = YOLO(str(weights_path))
    return _model
