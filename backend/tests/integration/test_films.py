"""Catalog endpoint tests — list, get, search, category filter, pagination."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_list_films_empty(client) -> None:
    resp = await client.get("/v1/films")
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["total"] == 0


@pytest.mark.asyncio
async def test_list_only_returns_published(client, make_film) -> None:
    await make_film(slug="pub-1")
    await make_film(slug="draft-1", status="draft")
    resp = await client.get("/v1/films")
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["slug"] == "pub-1"


@pytest.mark.asyncio
async def test_film_detail(client, make_film) -> None:
    film = await make_film(slug="big-buck-bunny", title="Big Buck Bunny")
    resp = await client.get(f"/v1/films/{film.id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "Big Buck Bunny"
    assert len(body["assets"]) == 1
    assert body["assets"][0]["kind"] == "hls_manifest"


@pytest.mark.asyncio
async def test_film_detail_404(client) -> None:
    resp = await client.get("/v1/films/99999")
    assert resp.status_code == 404
    assert resp.json()["detail"]["error"]["code"] == "film_not_found"


@pytest.mark.asyncio
async def test_film_search(client, make_film) -> None:
    await make_film(slug="bunny", title="Big Buck Bunny")
    await make_film(slug="sintel", title="Sintel")
    resp = await client.get("/v1/films/search", params={"q": "Bunny"})
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 1
    assert results[0]["title"] == "Big Buck Bunny"


@pytest.mark.asyncio
async def test_pagination(client, make_film) -> None:
    for i in range(5):
        await make_film(slug=f"film-{i}")
    resp = await client.get("/v1/films", params={"page": 1, "page_size": 2})
    body = resp.json()
    assert body["total"] == 5
    assert len(body["items"]) == 2
    resp2 = await client.get("/v1/films", params={"page": 3, "page_size": 2})
    assert len(resp2.json()["items"]) == 1


@pytest.mark.asyncio
async def test_category_filter(client, make_film) -> None:
    await make_film(slug="action-1", category_slugs=["action"])
    await make_film(slug="drama-1", category_slugs=["drama"])
    resp = await client.get("/v1/films", params={"category": "action"})
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["slug"] == "action-1"
