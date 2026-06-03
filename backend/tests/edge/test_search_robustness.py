"""Search edge cases: empty, special chars, SQL-LIKE wildcards, very long."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_search_empty_query_422(client) -> None:
    """Empty query is rejected by FastAPI validation (min_length=1)."""
    resp = await client.get("/v1/titles/search", params={"q": ""})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_search_wildcard_does_not_match_everything(client, make_title) -> None:
    """Before C3 fix, q='%' returned all titles because % was a LIKE wildcard.
    Now '%' is escaped — q='%' literally searches for the % character."""
    for slug in ("alpha", "bravo", "charlie"):
        await make_title(slug=slug, title=slug.title())

    resp = await client.get("/v1/titles/search", params={"q": "%"})
    assert resp.status_code == 200
    # None of the titles contain a literal '%' character
    assert resp.json() == []


@pytest.mark.asyncio
async def test_search_underscore_does_not_match_everything(client, make_title) -> None:
    """Same as above but for the _ wildcard."""
    await make_title(slug="a-title", title="A Title")
    resp = await client.get("/v1/titles/search", params={"q": "_"})
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_search_special_chars_safe(client, make_title) -> None:
    """SQL-injection-like patterns must just search literally, not execute."""
    await make_title(slug="real", title="Real Title")
    for nasty in ("'; DROP TABLE titles;--", '" OR 1=1 --', "<script>alert(1)</script>"):
        resp = await client.get("/v1/titles/search", params={"q": nasty})
        assert resp.status_code == 200
        assert resp.json() == []  # no title matches these strings


@pytest.mark.asyncio
async def test_search_very_long_query_is_clamped(client, make_title) -> None:
    """A 5000-char query should not 500 or DoS. Service caps at 100 chars."""
    await make_title(slug="x", title="X")
    resp = await client.get("/v1/titles/search", params={"q": "a" * 5000})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_search_case_insensitive(client, make_title) -> None:
    await make_title(slug="bbb", title="Big Buck Bunny")
    for q in ("bunny", "BUNNY", "Bunny", "bUnNy"):
        resp = await client.get("/v1/titles/search", params={"q": q})
        assert resp.status_code == 200
        assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_search_finds_in_synopsis(client, make_title) -> None:
    """Search hits title + synopsis + original_title."""
    await make_title(slug="x", title="Random Movie")
    # synopsis is "Test title." by default in make_title — let's confirm
    resp = await client.get("/v1/titles/search", params={"q": "Test title"})
    assert resp.status_code == 200
    assert len(resp.json()) == 1
