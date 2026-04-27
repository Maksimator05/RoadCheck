import io

import pytest
from httpx import AsyncClient
from PIL import Image, ImageDraw


def _road_jpeg() -> bytes:
    image = Image.new("RGB", (640, 360), (112, 112, 112))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 260, 640, 360), fill=(100, 100, 100))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    return buffer.getvalue()


def _road_png(*, with_pothole: bool) -> bytes:
    image = Image.new("RGB", (640, 360), (112, 112, 112))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 260, 640, 360), fill=(100, 100, 100))

    if with_pothole:
        draw.ellipse((220, 150, 380, 275), fill=(28, 28, 28))
        draw.ellipse((255, 175, 350, 245), fill=(15, 15, 15))

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.mark.asyncio
async def test_analyze_jpeg(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/analyze",
        headers=auth_headers,
        files={"file": ("photo.jpg", io.BytesIO(_road_jpeg()), "image/jpeg")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "defects" in data
    assert "count" in data
    assert "analysis_id" in data
    assert "image_width" in data
    assert "image_height" in data
    assert data["image_width"] == 640
    assert data["image_height"] == 360


@pytest.mark.asyncio
async def test_analyze_unsupported_type(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/analyze",
        headers=auth_headers,
        files={"file": ("file.txt", io.BytesIO(b"hello"), "text/plain")},
    )
    assert resp.status_code == 415


@pytest.mark.asyncio
async def test_analyze_no_auth(client: AsyncClient):
    resp = await client.post(
        "/analyze",
        files={"file": ("photo.jpg", io.BytesIO(_road_jpeg()), "image/jpeg")},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_analyze_invalid_image_payload(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/analyze",
        headers=auth_headers,
        files={"file": ("broken.jpg", io.BytesIO(b"not-a-real-image"), "image/jpeg")},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_analyze_clean_road_returns_dimensions(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/analyze",
        headers=auth_headers,
        files={"file": ("clean-road.png", io.BytesIO(_road_png(with_pothole=False)), "image/png")},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["image_width"] == 640
    assert data["image_height"] == 360
    assert data["count"] == 0


@pytest.mark.asyncio
async def test_analyze_detects_synthetic_pothole(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/analyze",
        headers=auth_headers,
        files={"file": ("pothole-road.png", io.BytesIO(_road_png(with_pothole=True)), "image/png")},
    )

    assert resp.status_code == 200
    data = resp.json()
    potholes = [defect for defect in data["defects"] if defect["type"] == "pothole"]

    assert data["count"] >= 1
    assert potholes
