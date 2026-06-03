"""Pagination + filter validation edge cases."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_page_zero_rejected(client) -> None:
    """FastAPI rejects page<1 at validation."""
    resp = await client.get("/v1/titles", params={"page": 0})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_page_very_large_returns_empty(client, make_title) -> None:
    await make_title(slug="x")
    resp = await client.get("/v1/titles", params={"page": 999999, "page_size": 50})
    assert resp.status_code == 200
    assert resp.json()["items"] == []
    assert resp.json()["total"] == 1  # total reflects DB, not page


@pytest.mark.asyncio
async def test_page_size_capped_at_100(client) -> None:
    resp = await client.get("/v1/titles", params={"page_size": 999})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_page_size_zero_rejected(client) -> None:
    resp = await client.get("/v1/titles", params={"page_size": 0})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_invalid_sort_field_rejected(client) -> None:
    """C9 — arbitrary sort field must be rejected, not silently fall back."""
    resp = await client.get("/v1/titles", params={"sort": "drop_table; --"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_valid_sort_fields_accepted(client) -> None:
    for s in ("published_at", "-published_at", "title", "-title", "view_count", "-view_count"):
        resp = await client.get("/v1/titles", params={"sort": s})
        assert resp.status_code == 200, f"sort={s} should be accepted but got {resp.status_code}"


@pytest.mark.asyncio
async def test_invalid_type_filter_rejected(client) -> None:
    resp = await client.get("/v1/titles", params={"type": "podcast"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_year_range_filter_inclusive(client, make_title) -> None:
    await make_title(slug="a", release_year=2000)
    await make_title(slug="b", release_year=2010)
    await make_title(slug="c", release_year=2020)
    resp = await client.get("/v1/titles", params={"year_from": 2000, "year_to": 2020})
    assert resp.json()["total"] == 3
