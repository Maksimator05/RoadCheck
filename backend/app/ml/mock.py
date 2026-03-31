def mock_predict(image_path: str) -> list[dict]:
    return [
        {"type": "pothole", "confidence": 0.94, "bbox": [120, 80, 200, 160], "severity": "high"},
        {"type": "crack", "confidence": 0.81, "bbox": [300, 150, 420, 180], "severity": "medium"},
    ]
