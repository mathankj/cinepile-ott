"""Reactions + My List."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_set_and_clear_reaction(auth_client, make_title) -> None:
    client, _, _ = auth_client
    t = await make_title(slug="m")
    r = await client.put(f"/v1/titles/{t.id}/reaction", json={"kind": "thumbs_up"})
    assert r.status_code == 200
    assert r.json()["kind"] == "thumbs_up"

    # Switching reaction = upsert
    r2 = await client.put(f"/v1/titles/{t.id}/reaction", json={"kind": "double_thumbs_up"})
    assert r2.json()["kind"] == "double_thumbs_up"

    my = (await client.get("/v1/me/reactions")).json()
    assert len(my["items"]) == 1
    assert my["items"][0]["kind"] == "double_thumbs_up"

    rm = await client.delete(f"/v1/titles/{t.id}/reaction")
    assert rm.status_code == 204
    assert (await client.get("/v1/me/reactions")).json()["items"] == []


@pytest.mark.asyncio
async def test_reaction_invalid_kind(auth_client, make_title) -> None:
    client, _, _ = auth_client
    t = await make_title(slug="m")
    r = await client.put(f"/v1/titles/{t.id}/reaction", json={"kind": "shrug"})
    assert r.status_code == 422  # pydantic rejects before we reach the service


@pytest.mark.asyncio
async def test_watchlist_add_remove_list(auth_client, make_title) -> None:
    client, _, _ = auth_client
    t = await make_title(slug="m")

    r = await client.post(f"/v1/me/list/{t.id}")
    assert r.status_code == 200
    assert r.json()["added"] is True

    # Idempotent — second add returns added=False
    r2 = await client.post(f"/v1/me/list/{t.id}")
    assert r2.json()["added"] is False

    lst = (await client.get("/v1/me/list")).json()
    assert len(lst["items"]) == 1
    assert lst["items"][0]["title"]["id"] == t.id

    rm = await client.delete(f"/v1/me/list/{t.id}")
    assert rm.status_code == 204
    assert (await client.get("/v1/me/list")).json()["items"] == []


@pytest.mark.asyncio
async def test_watchlist_unknown_title(auth_client) -> None:
    client, _, _ = auth_client
    r = await client.post("/v1/me/list/99999")
    assert r.status_code == 404
