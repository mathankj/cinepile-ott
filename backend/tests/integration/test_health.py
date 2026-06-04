"""Smoke test that the app boots and /healthz responds."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_healthz_returns_ok(client: AsyncClient) -> None:
    """Liveness — must always 200 regardless of DB state."""
    resp = await client.get("/healthz")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "version" in body


@pytest.mark.asyncio
async def test_readyz_returns_db_status(client: AsyncClient) -> None:
    """Readiness — checks DB. 200 in tests because in-memory SQLite is always up."""
    resp = await client.get("/readyz")
    assert resp.status_code in (200, 503)
    body = resp.json()
    assert "db" in body
    assert "storage" in body


@pytest.mark.asyncio
async def test_openapi_is_served(client: AsyncClient) -> None:
    resp = await client.get("/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()
    assert schema["info"]["title"] == "CinePile API"
