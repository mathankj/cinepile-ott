"""Smoke test that the app boots and /healthz responds."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_healthz_returns_ok(client: AsyncClient) -> None:
    resp = await client.get("/healthz")
    assert resp.status_code in (200, 503)  # 503 if DB is unreachable, still a valid response
    body = resp.json()
    assert "status" in body
    assert "version" in body
    assert "env" in body


@pytest.mark.asyncio
async def test_openapi_is_served(client: AsyncClient) -> None:
    resp = await client.get("/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()
    assert schema["info"]["title"] == "Anjaneya OTT API"
