import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from app.ml import inference
from app.ml import model as ml_model


class _FakeModel:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def predict(self, **kwargs):
        self.calls.append(kwargs)
        if isinstance(self.result, list):
            index = min(len(self.calls) - 1, len(self.result) - 1)
            return [self.result[index]]
        return [self.result]


def _save_image(path: Path) -> None:
    Image.new("RGB", (320, 200), (120, 120, 120)).save(path, format="JPEG")


@contextmanager
def _workspace_temp_file(suffix: str):
    temp_dir = Path(__file__).resolve().parent / ".tmp"
    temp_dir.mkdir(exist_ok=True)
    file_descriptor, file_path = tempfile.mkstemp(suffix=suffix, dir=temp_dir)
    os.close(file_descriptor)
    path = Path(file_path)
    try:
        yield path
    finally:
        path.unlink(missing_ok=True)


def test_predict_normalizes_yolo_labels(monkeypatch):
    with _workspace_temp_file(".jpg") as image_path:
        _save_image(image_path)

        fake_result = SimpleNamespace(
            names={0: "D00", 3: "D40"},
            boxes=[
                SimpleNamespace(conf=[0.73], cls=[0], xyxy=[[10.2, 20.4, 90.8, 100.1]]),
                SimpleNamespace(conf=[0.91], cls=[3], xyxy=[[120.0, 40.0, 220.0, 150.0]]),
            ],
        )
        fake_model = _FakeModel(fake_result)

        monkeypatch.setattr(inference.settings, "USE_MOCK_ML", False)
        monkeypatch.setattr(inference.settings, "ML_CONFIDENCE_THRESHOLD", 0.19)
        monkeypatch.setattr(inference.settings, "ML_POTHOLE_CONFIDENCE_THRESHOLD", 0.31)
        monkeypatch.setattr(inference.settings, "ML_CRACK_CONFIDENCE_THRESHOLD", 0.20)
        monkeypatch.setattr(inference.settings, "ML_IOU_THRESHOLD", 0.29)
        monkeypatch.setattr(inference.settings, "ML_DEVICE", "cpu")
        monkeypatch.setattr(ml_model, "load_model", lambda: fake_model)
        monkeypatch.setattr(inference, "_is_valid_detection", lambda *args, **kwargs: True)
        monkeypatch.setattr(inference, "_tighten_bbox_to_road", lambda bbox, _road_mask: bbox)
        monkeypatch.setattr(
            inference,
            "_iter_inference_sources",
            lambda image_path_value, _image, _road_mask: [(image_path_value, 0, 0, False)],
        )

        result = inference.predict(str(image_path))

        assert [item["type"] for item in result["defects"]] == ["longitudinal_crack", "pothole"]
        assert result["image_width"] == 320
        assert result["image_height"] == 200
        assert fake_model.calls[0]["conf"] == 0.19
        assert fake_model.calls[0]["iou"] == 0.29
        assert fake_model.calls[0]["device"] == "cpu"
        assert fake_model.calls[0]["source"] == str(image_path)


def test_predict_uses_tile_offsets_and_per_class_thresholds(monkeypatch):
    with _workspace_temp_file(".jpg") as image_path:
        _save_image(image_path)

        full_result = SimpleNamespace(
            names={0: "D00", 3: "D40"},
            boxes=[
                SimpleNamespace(conf=[0.22], cls=[0], xyxy=[[15.0, 20.0, 95.0, 80.0]]),
                SimpleNamespace(conf=[0.41], cls=[3], xyxy=[[110.0, 40.0, 180.0, 120.0]]),
            ],
        )
        tile_result = SimpleNamespace(
            names={0: "D00", 3: "D40"},
            boxes=[
                SimpleNamespace(conf=[0.27], cls=[0], xyxy=[[20.0, 15.0, 70.0, 65.0]]),
                SimpleNamespace(conf=[0.52], cls=[3], xyxy=[[35.0, 30.0, 95.0, 88.0]]),
            ],
        )
        fake_model = _FakeModel([full_result, tile_result])

        monkeypatch.setattr(inference.settings, "USE_MOCK_ML", False)
        monkeypatch.setattr(inference.settings, "ML_CONFIDENCE_THRESHOLD", 0.20)
        monkeypatch.setattr(inference.settings, "ML_POTHOLE_CONFIDENCE_THRESHOLD", 0.50)
        monkeypatch.setattr(inference.settings, "ML_CRACK_CONFIDENCE_THRESHOLD", 0.25)
        monkeypatch.setattr(inference.settings, "ML_IOU_THRESHOLD", 0.33)
        monkeypatch.setattr(inference.settings, "ML_DEVICE", "cpu")
        monkeypatch.setattr(ml_model, "load_model", lambda: fake_model)
        monkeypatch.setattr(inference, "_is_valid_detection", lambda *args, **kwargs: True)
        monkeypatch.setattr(inference, "_tighten_bbox_to_road", lambda bbox, _road_mask: bbox)
        monkeypatch.setattr(
            inference,
            "_iter_inference_sources",
            lambda image_path_value, _image, _road_mask: [
                (image_path_value, 0, 0, False),
                ("tile-source", 100, 60, True),
            ],
        )

        result = inference.predict(str(image_path))

        assert [item["type"] for item in result["defects"]] == ["longitudinal_crack", "pothole"]
        assert result["defects"][0]["bbox"] == [120, 75, 170, 125]
        assert result["defects"][1]["bbox"] == [135, 90, 195, 148]
        assert fake_model.calls[0]["conf"] == 0.20
        assert fake_model.calls[1]["conf"] == 0.20


def test_predict_rejects_invalid_image():
    with _workspace_temp_file(".jpg") as image_path:
        image_path.write_bytes(b"broken")

        with pytest.raises(inference.InvalidImageError):
            inference.predict(str(image_path))
