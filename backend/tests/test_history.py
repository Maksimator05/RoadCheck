import io
import uuid

import pytest
from httpx import AsyncClient


def _fake_jpeg() -> bytes:
    return b"\xff\xd8\xff\xe0" + b"\x00" * 100


async def _create_analysis(client: AsyncClient, headers: dict) -> str:
    """Upload a photo and return analysis_id."""
    resp = await client.post(
        "/analyze",
        headers=headers,
        files={"file": ("road.jpg", io.BytesIO(_fake_jpeg()), "image/jpeg")},
    )
    return resp.json()["analysis_id"]


@pytest.mark.asyncio
async def test_history_list(client: AsyncClient, auth_headers: dict):
    await _create_analysis(client, auth_headers)

    resp = await client.get("/history", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_history_detail(client: AsyncClient, auth_headers: dict):
    aid = await _create_analysis(client, auth_headers)

    resp = await client.get(f"/history/{aid}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == aid


@pytest.mark.asyncio
async def test_history_pdf(client: AsyncClient, auth_headers: dict):
    aid = await _create_analysis(client, auth_headers)

    resp = await client.get(f"/history/{aid}/pdf", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"


@pytest.mark.asyncio
async def test_history_not_found(client: AsyncClient, auth_headers: dict):
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"/history/{fake_id}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_history_delete(client: AsyncClient, auth_headers: dict):
    aid = await _create_analysis(client, auth_headers)

    resp = await client.delete(f"/history/{aid}", headers=auth_headers)
    assert resp.status_code == 204

    # Confirm it's gone
    resp = await client.get(f"/history/{aid}", headers=auth_headers)
    assert resp.status_code == 404
