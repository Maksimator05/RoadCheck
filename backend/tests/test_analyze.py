import io

import pytest
from httpx import AsyncClient


def _fake_jpeg() -> bytes:
    """Minimal JPEG-like bytes (enough to pass content_type check)."""
    return b"\xff\xd8\xff\xe0" + b"\x00" * 100


@pytest.mark.asyncio
async def test_analyze_jpeg(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/analyze",
        headers=auth_headers,
        files={"file": ("photo.jpg", io.BytesIO(_fake_jpeg()), "image/jpeg")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "defects" in data
    assert "count" in data
    assert "analysis_id" in data


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
        files={"file": ("photo.jpg", io.BytesIO(_fake_jpeg()), "image/jpeg")},
    )
    assert resp.status_code == 401
