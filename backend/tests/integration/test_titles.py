"""Catalog endpoint tests — titles list/detail/search/filter, seasons, episodes."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_list_titles_empty(client) -> None:
    resp = await client.get("/v1/titles")
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["total"] == 0


@pytest.mark.asyncio
async def test_list_only_returns_published(client, make_title) -> None:
    await make_title(slug="pub-1")
    await make_title(slug="draft-1", status="draft")
    resp = await client.get("/v1/titles")
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["slug"] == "pub-1"


@pytest.mark.asyncio
async def test_filter_by_type(client, make_title, make_series_with_episodes) -> None:
    await make_title(slug="a-movie", type="movie")
    await make_series_with_episodes(slug="a-series", seasons=1, episodes_per_season=1)
    movies = (await client.get("/v1/titles", params={"type": "movie"})).json()
    series = (await client.get("/v1/titles", params={"type": "series"})).json()
    assert {i["slug"] for i in movies["items"]} == {"a-movie"}
    assert {i["slug"] for i in series["items"]} == {"a-series"}


@pytest.mark.asyncio
async def test_filter_by_genre(client, make_title) -> None:
    await make_title(slug="action-1", genres=["action"])
    await make_title(slug="drama-1", genres=["drama"])
    resp = await client.get("/v1/titles", params={"genre": "action"})
    body = resp.json()
    assert body["total"] == 1 and body["items"][0]["slug"] == "action-1"


@pytest.mark.asyncio
async def test_filter_by_language(client, make_title) -> None:
    await make_title(slug="en-1", original_language="en")
    await make_title(slug="ta-1", original_language="ta")
    resp = await client.get("/v1/titles", params={"language": "ta"})
    body = resp.json()
    assert body["total"] == 1 and body["items"][0]["slug"] == "ta-1"


@pytest.mark.asyncio
async def test_filter_by_country(client, make_title) -> None:
    await make_title(slug="in-1", countries=["IN"])
    await make_title(slug="us-1", countries=["US"])
    resp = await client.get("/v1/titles", params={"country": "IN"})
    body = resp.json()
    assert body["total"] == 1 and body["items"][0]["slug"] == "in-1"


@pytest.mark.asyncio
async def test_filter_by_year_range(client, make_title) -> None:
    await make_title(slug="old", release_year=1999)
    await make_title(slug="mid", release_year=2010)
    await make_title(slug="new", release_year=2024)
    resp = await client.get("/v1/titles", params={"year_from": 2005, "year_to": 2020})
    slugs = {i["slug"] for i in resp.json()["items"]}
    assert slugs == {"mid"}


@pytest.mark.asyncio
async def test_title_detail_movie(client, make_title) -> None:
    t = await make_title(slug="big-buck-bunny")
    resp = await client.get(f"/v1/titles/{t.id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["type"] == "movie"
    assert len(body["assets"]) == 1
    assert body["seasons"] == []


@pytest.mark.asyncio
async def test_title_detail_series_shows_seasons(client, make_series_with_episodes) -> None:
    s = await make_series_with_episodes(slug="the-show", seasons=2, episodes_per_season=3)
    resp = await client.get(f"/v1/titles/{s.id}")
    body = resp.json()
    assert body["type"] == "series"
    assert len(body["seasons"]) == 2
    assert body["seasons"][0]["episode_count"] == 3


@pytest.mark.asyncio
async def test_get_season_detail(client, make_series_with_episodes) -> None:
    s = await make_series_with_episodes(slug="the-show", seasons=1, episodes_per_season=4)
    resp = await client.get(f"/v1/titles/{s.id}/seasons/1")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["episodes"]) == 4
    assert body["episodes"][0]["episode_number"] == 1


@pytest.mark.asyncio
async def test_get_episode_detail(client, make_series_with_episodes) -> None:
    s = await make_series_with_episodes(slug="the-show", seasons=1, episodes_per_season=2)
    resp = await client.get(f"/v1/titles/{s.id}/seasons/1/episodes/2")
    assert resp.status_code == 200
    assert resp.json()["episode_number"] == 2


@pytest.mark.asyncio
async def test_search(client, make_title) -> None:
    await make_title(slug="bunny", title="Big Buck Bunny")
    await make_title(slug="sintel", title="Sintel")
    resp = await client.get("/v1/titles/search", params={"q": "bunny"})
    assert len(resp.json()) == 1
