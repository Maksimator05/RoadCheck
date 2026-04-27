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
        return [self.result]


def _save_image(path):
    Image.new("RGB", (320, 200), (120, 120, 120)).save(path, format="JPEG")


def test_predict_normalizes_yolo_labels(monkeypatch, tmp_path):
    image_path = tmp_path / "road.jpg"
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
    monkeypatch.setattr(inference.settings, "ML_CONFIDENCE_THRESHOLD", 0.31)
    monkeypatch.setattr(inference.settings, "ML_IOU_THRESHOLD", 0.29)
    monkeypatch.setattr(inference.settings, "ML_DEVICE", "cpu")
    monkeypatch.setattr(ml_model, "load_model", lambda: fake_model)

    result = inference.predict(str(image_path))

    assert [item["type"] for item in result["defects"]] == ["crack", "pothole"]
    assert result["image_width"] == 320
    assert result["image_height"] == 200
    assert fake_model.calls[0]["conf"] == 0.31
    assert fake_model.calls[0]["iou"] == 0.29
    assert fake_model.calls[0]["device"] == "cpu"
    assert fake_model.calls[0]["source"] == str(image_path)


def test_predict_rejects_invalid_image(tmp_path):
    image_path = tmp_path / "broken.jpg"
    image_path.write_bytes(b"broken")

    with pytest.raises(inference.InvalidImageError):
        inference.predict(str(image_path))
