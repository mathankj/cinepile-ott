"""Watch-history endpoint tests."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_progress_requires_auth(client, make_film) -> None:
    film = await make_film(slug="x")
    resp = await client.post(
        f"/v1/history/{film.id}/progress", json={"position_sec": 30, "total_sec": 600}
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_progress_upserts(auth_client, make_film) -> None:
    client, _, _ = auth_client
    film = await make_film(slug="x")
    r1 = await client.post(
        f"/v1/history/{film.id}/progress", json={"position_sec": 100, "total_sec": 1000}
    )
    assert r1.status_code == 204
    r2 = await client.post(
        f"/v1/history/{film.id}/progress", json={"position_sec": 500, "total_sec": 1000}
    )
    assert r2.status_code == 204
    items = (await client.get("/v1/history")).json()["items"]
    assert len(items) == 1
    assert items[0]["position_sec"] == 500
    assert items[0]["completed"] is False


@pytest.mark.asyncio
async def test_completion_threshold(auth_client, make_film) -> None:
    client, _, _ = auth_client
    film = await make_film(slug="x")
    await client.post(
        f"/v1/history/{film.id}/progress", json={"position_sec": 950, "total_sec": 1000}
    )
    items = (await client.get("/v1/history")).json()["items"]
    assert items[0]["completed"] is True


@pytest.mark.asyncio
async def test_continue_watching_excludes_deleted_film(auth_client, make_film, db_session) -> None:
    from datetime import datetime, timezone

    client, _, _ = auth_client
    film = await make_film(slug="x")
    await client.post(
        f"/v1/history/{film.id}/progress", json={"position_sec": 100, "total_sec": 1000}
    )
    # Soft-delete the film
    db_film = await db_session.get(type(film), film.id)
    db_film.deleted_at = datetime.now(tz=timezone.utc)
    await db_session.commit()
    items = (await client.get("/v1/history")).json()["items"]
    assert items == []


@pytest.mark.asyncio
async def test_delete_history(auth_client, make_film) -> None:
    client, _, _ = auth_client
    film = await make_film(slug="x")
    await client.post(
        f"/v1/history/{film.id}/progress", json={"position_sec": 50, "total_sec": 1000}
    )
    r = await client.delete(f"/v1/history/{film.id}")
    assert r.status_code == 204
    items = (await client.get("/v1/history")).json()["items"]
    assert items == []
