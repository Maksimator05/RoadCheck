import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register(client: AsyncClient):
    resp = await client.post("/auth/register", json={
        "email": "new@example.com",
        "password": "strongpass1",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_duplicate(client: AsyncClient):
    payload = {"email": "dup@example.com", "password": "pass1234"}
    await client.post("/auth/register", json=payload)
    resp = await client.post("/auth/register", json=payload)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_login(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "login@example.com",
        "password": "pass1234",
    })
    resp = await client.post("/auth/login", json={
        "email": "login@example.com",
        "password": "pass1234",
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "wrong@example.com",
        "password": "pass1234",
    })
    resp = await client.post("/auth/login", json={
        "email": "wrong@example.com",
        "password": "badpass",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh(client: AsyncClient):
    reg = await client.post("/auth/register", json={
        "email": "refresh@example.com",
        "password": "pass1234",
    })
    refresh_token = reg.json()["refresh_token"]

    resp = await client.post("/auth/refresh", json={
        "refresh_token": refresh_token,
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_logout(client: AsyncClient):
    reg = await client.post("/auth/register", json={
        "email": "logout@example.com",
        "password": "pass1234",
    })
    refresh_token = reg.json()["refresh_token"]

    resp = await client.post("/auth/logout", json={
        "refresh_token": refresh_token,
    })
    assert resp.status_code == 204
