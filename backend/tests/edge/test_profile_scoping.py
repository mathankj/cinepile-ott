"""Per-profile scoping (X-Profile-Id header) + kids-content enforcement.

Covers:
  - watchlist / watch progress / reactions are isolated between profiles
  - no header = legacy NULL-profile scope (pre-profile data stays reachable)
  - the header is verified server-side: another user's profile id or garbage
    is silently ignored (treated as no profile), never trusted
  - kid profiles: 403 kid_profile_restricted on non-U playback, U plays fine,
    home rows exclude non-U titles
  - the /v1/home cache is keyed per profile (no leak between profiles)
  - playback resume hints are per profile
"""
from __future__ import annotations

import pytest


def _ph(profile: dict) -> dict[str, str]:
    """Request headers selecting the given profile."""
    return {"X-Profile-Id": str(profile["id"])}


async def _create_profile(client, name: str, kind: str = "adult", headers: dict | None = None) -> dict:
    resp = await client.post(
        "/v1/me/profiles",
        json={"name": name, "avatar": "default", "kind": kind},
        headers=headers or {},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _make_free(db_session, title_id: int, *, age_rating: str | None = "U") -> None:
    """Flip a seeded title to is_free (so /play works without a subscription)
    and set its age rating — the knob the kid gate keys on."""
    from app.models.title import Title

    t = await db_session.get(Title, title_id)
    t.is_free = True
    t.age_rating = age_rating
    await db_session.commit()


def _home_item_ids(home_json: dict) -> set[int]:
    return {item["id"] for row in home_json["rows"] for item in row["items"]}


def _home_row(home_json: dict, kind: str) -> dict | None:
    return next((r for r in home_json["rows"] if r["kind"] == kind), None)


# ---- Scoping: separate data per profile ---------------------------------------


@pytest.mark.asyncio
async def test_watchlist_scoped_per_profile(auth_client, make_title) -> None:
    client, _, _ = auth_client
    t = await make_title(slug="scoped-list")
    pa = await _create_profile(client, "Alpha")
    pb = await _create_profile(client, "Beta")

    r = await client.post(f"/v1/me/list/{t.id}", headers=_ph(pa))
    assert r.status_code == 200 and r.json()["added"] is True

    in_a = await client.get("/v1/me/list", headers=_ph(pa))
    in_b = await client.get("/v1/me/list", headers=_ph(pb))
    no_header = await client.get("/v1/me/list")
    assert [i["title"]["id"] for i in in_a.json()["items"]] == [t.id]
    assert in_b.json()["items"] == []
    assert no_header.json()["items"] == []

    # Removing under the WRONG profile must not touch Alpha's list.
    r = await client.delete(f"/v1/me/list/{t.id}", headers=_ph(pb))
    assert r.status_code == 404
    still_a = await client.get("/v1/me/list", headers=_ph(pa))
    assert len(still_a.json()["items"]) == 1


@pytest.mark.asyncio
async def test_progress_and_continue_watching_scoped(auth_client, make_title) -> None:
    client, _, _ = auth_client
    t = await make_title(slug="scoped-progress")
    pa = await _create_profile(client, "Alpha")
    pb = await _create_profile(client, "Beta")

    r = await client.post(
        f"/v1/titles/{t.id}/progress",
        json={"position_sec": 300, "total_sec": 3600},
        headers=_ph(pa),
    )
    assert r.status_code == 204, r.text

    cw_a = await client.get("/v1/me/continue-watching", headers=_ph(pa))
    cw_b = await client.get("/v1/me/continue-watching", headers=_ph(pb))
    cw_none = await client.get("/v1/me/continue-watching")
    assert [i["title"]["id"] for i in cw_a.json()["items"]] == [t.id]
    assert cw_b.json()["items"] == []
    assert cw_none.json()["items"] == []

    # Full history is scoped the same way.
    h_a = await client.get("/v1/me/history", headers=_ph(pa))
    h_b = await client.get("/v1/me/history", headers=_ph(pb))
    assert h_a.json()["total"] == 1
    assert h_b.json()["total"] == 0

    # Hiding from continue-watching on Beta must 404 (no Beta rows) and leave
    # Alpha's row visible.
    r = await client.delete(f"/v1/me/continue-watching/{t.id}", headers=_ph(pb))
    assert r.status_code == 404
    cw_a2 = await client.get("/v1/me/continue-watching", headers=_ph(pa))
    assert len(cw_a2.json()["items"]) == 1


@pytest.mark.asyncio
async def test_reactions_scoped_per_profile(auth_client, make_title) -> None:
    client, _, _ = auth_client
    t = await make_title(slug="scoped-reaction")
    pa = await _create_profile(client, "Alpha")
    pb = await _create_profile(client, "Beta")

    r = await client.put(
        f"/v1/titles/{t.id}/reaction", json={"kind": "thumbs_up"}, headers=_ph(pa)
    )
    assert r.status_code == 200, r.text

    # Same title, different profile, different opinion — both rows coexist.
    r = await client.put(
        f"/v1/titles/{t.id}/reaction", json={"kind": "thumbs_down"}, headers=_ph(pb)
    )
    assert r.status_code == 200, r.text

    rx_a = await client.get("/v1/me/reactions", headers=_ph(pa))
    rx_b = await client.get("/v1/me/reactions", headers=_ph(pb))
    rx_none = await client.get("/v1/me/reactions")
    assert [i["kind"] for i in rx_a.json()["items"]] == ["thumbs_up"]
    assert [i["kind"] for i in rx_b.json()["items"]] == ["thumbs_down"]
    assert rx_none.json()["items"] == []

    # Clearing Beta's reaction leaves Alpha's intact.
    r = await client.delete(f"/v1/titles/{t.id}/reaction", headers=_ph(pb))
    assert r.status_code == 204
    assert len((await client.get("/v1/me/reactions", headers=_ph(pa))).json()["items"]) == 1
    assert (await client.get("/v1/me/reactions", headers=_ph(pb))).json()["items"] == []


# ---- Header trust boundary -----------------------------------------------------


@pytest.mark.asyncio
async def test_other_users_profile_header_is_ignored(auth_client, make_user, make_title) -> None:
    """Naming someone else's profile id must NOT scope into (or leak from)
    their data — it degrades to the legacy no-profile scope."""
    client, _, _ = auth_client  # user1, auth header already set on the client
    t = await make_title(slug="foreign-profile")

    await make_user(email="victim@example.com", password="password123")
    login2 = await client.post(
        "/v1/auth/login", json={"email": "victim@example.com", "password": "password123"}
    )
    token2 = login2.json()["tokens"]["access_token"]
    auth2 = {"Authorization": f"Bearer {token2}"}
    victim_profile = await _create_profile(client, "Victim", headers=auth2)

    # user1 writes while claiming the victim's profile id.
    r = await client.post(f"/v1/me/list/{t.id}", headers=_ph(victim_profile))
    assert r.status_code == 200

    # The write landed in user1's legacy scope — not in the victim's profile.
    assert len((await client.get("/v1/me/list")).json()["items"]) == 1
    victim_list = await client.get(
        "/v1/me/list", headers={**auth2, **_ph(victim_profile)}
    )
    assert victim_list.json()["items"] == []


@pytest.mark.asyncio
async def test_garbage_profile_header_falls_back_to_legacy(auth_client, make_title) -> None:
    client, _, _ = auth_client
    t = await make_title(slug="garbage-header")

    r = await client.post(f"/v1/me/list/{t.id}", headers={"X-Profile-Id": "banana"})
    assert r.status_code == 200

    # Garbage header on read behaves exactly like no header.
    listed = await client.get("/v1/me/list", headers={"X-Profile-Id": "999999"})
    assert [i["title"]["id"] for i in listed.json()["items"]] == [t.id]


@pytest.mark.asyncio
async def test_no_header_keeps_legacy_scope_separate(auth_client, make_title) -> None:
    """Pre-profile clients (no header) keep working against NULL-profile rows,
    and those rows never bleed into a profile's view."""
    client, _, _ = auth_client
    t = await make_title(slug="legacy-scope")
    pa = await _create_profile(client, "Alpha")

    r = await client.post(f"/v1/me/list/{t.id}")  # no header → NULL scope
    assert r.status_code == 200

    assert len((await client.get("/v1/me/list")).json()["items"]) == 1
    assert (await client.get("/v1/me/list", headers=_ph(pa))).json()["items"] == []


# ---- Kids enforcement ----------------------------------------------------------


@pytest.mark.asyncio
async def test_kid_profile_blocked_from_non_u_movie(auth_client, make_title, db_session) -> None:
    client, _, _ = auth_client
    t = await make_title(slug="adults-only")
    await _make_free(db_session, t.id, age_rating="A")
    kid = await _create_profile(client, "Junior", kind="kid")
    adult = await _create_profile(client, "Parent", kind="adult")

    r = await client.get(f"/v1/titles/{t.id}/play", headers=_ph(kid))
    assert r.status_code == 403, r.text
    assert r.json()["detail"]["error"]["code"] == "kid_profile_restricted"

    # Same title plays fine for an adult profile and with no profile at all.
    assert (await client.get(f"/v1/titles/{t.id}/play", headers=_ph(adult))).status_code == 200
    assert (await client.get(f"/v1/titles/{t.id}/play")).status_code == 200


@pytest.mark.asyncio
async def test_kid_profile_plays_u_rated_movie(auth_client, make_title, db_session) -> None:
    client, _, _ = auth_client
    t = await make_title(slug="kids-ok")
    await _make_free(db_session, t.id, age_rating="U")
    kid = await _create_profile(client, "Junior", kind="kid")

    r = await client.get(f"/v1/titles/{t.id}/play", headers=_ph(kid))
    assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_kid_profile_blocked_when_rating_missing(auth_client, make_title, db_session) -> None:
    """NULL age_rating fails closed — unrated content is not kid-safe."""
    client, _, _ = auth_client
    t = await make_title(slug="unrated")
    await _make_free(db_session, t.id, age_rating=None)
    kid = await _create_profile(client, "Junior", kind="kid")

    r = await client.get(f"/v1/titles/{t.id}/play", headers=_ph(kid))
    assert r.status_code == 403
    assert r.json()["detail"]["error"]["code"] == "kid_profile_restricted"


@pytest.mark.asyncio
async def test_kid_profile_blocked_from_non_u_episode(
    auth_client, make_series_with_episodes, db_session
) -> None:
    """Episodes inherit the parent series' age rating for the kid gate."""
    client, _, _ = auth_client
    s = await make_series_with_episodes(slug="grim-show", seasons=1, episodes_per_season=1)
    await _make_free(db_session, s.id, age_rating="U/A")  # U/A is NOT kid-safe
    kid = await _create_profile(client, "Junior", kind="kid")
    adult = await _create_profile(client, "Parent", kind="adult")

    season = (await client.get(f"/v1/titles/{s.id}/seasons/1")).json()
    ep_id = season["episodes"][0]["id"]

    r = await client.get(f"/v1/episodes/{ep_id}/play", headers=_ph(kid))
    assert r.status_code == 403
    assert r.json()["detail"]["error"]["code"] == "kid_profile_restricted"
    assert (await client.get(f"/v1/episodes/{ep_id}/play", headers=_ph(adult))).status_code == 200


@pytest.mark.asyncio
async def test_kid_home_rows_exclude_non_u_titles(auth_client, make_title, db_session) -> None:
    client, _, _ = auth_client
    safe = await make_title(slug="u-rated-fun")  # conftest defaults age_rating="U"
    grim = await make_title(slug="a-rated-grim")
    from app.models.title import Title

    t = await db_session.get(Title, grim.id)
    t.age_rating = "A"
    await db_session.commit()

    kid = await _create_profile(client, "Junior", kind="kid")
    adult = await _create_profile(client, "Parent", kind="adult")

    adult_home = (await client.get("/v1/home", headers=_ph(adult))).json()
    kid_home = (await client.get("/v1/home", headers=_ph(kid))).json()

    assert grim.id in _home_item_ids(adult_home)  # sanity: it IS on adult home
    assert grim.id not in _home_item_ids(kid_home)
    assert safe.id in _home_item_ids(kid_home)


# ---- Cache isolation -----------------------------------------------------------


@pytest.mark.asyncio
async def test_home_cache_does_not_leak_between_profiles(auth_client, make_title) -> None:
    """/v1/home is TTL-cached server-side; the key must include the profile so
    profile A's personalized rows are never served to profile B."""
    client, _, _ = auth_client
    t = await make_title(slug="cache-probe")
    pa = await _create_profile(client, "Alpha")
    pb = await _create_profile(client, "Beta")

    r = await client.post(f"/v1/me/list/{t.id}", headers=_ph(pa))
    assert r.status_code == 200

    # Prime the cache for Alpha — My List row present.
    home_a = (await client.get("/v1/home", headers=_ph(pa))).json()
    assert _home_row(home_a, "my_list") is not None

    # Immediately read as Beta and with no profile: a shared cache key would
    # replay Alpha's rows here.
    home_b = (await client.get("/v1/home", headers=_ph(pb))).json()
    home_none = (await client.get("/v1/home")).json()
    assert _home_row(home_b, "my_list") is None
    assert _home_row(home_none, "my_list") is None

    # And Alpha's cached copy still has it.
    home_a2 = (await client.get("/v1/home", headers=_ph(pa))).json()
    assert _home_row(home_a2, "my_list") is not None


# ---- Resume hints --------------------------------------------------------------


@pytest.mark.asyncio
async def test_playback_resume_hint_is_per_profile(auth_client, make_title, db_session) -> None:
    client, _, _ = auth_client
    t = await make_title(slug="resume-scoped")
    await _make_free(db_session, t.id, age_rating="U")
    pa = await _create_profile(client, "Alpha")
    pb = await _create_profile(client, "Beta")

    for profile, pos in ((pa, 100), (pb, 200)):
        r = await client.post(
            f"/v1/titles/{t.id}/progress",
            json={"position_sec": pos, "total_sec": 3600},
            headers=_ph(profile),
        )
        assert r.status_code == 204

    assert (await client.get(f"/v1/titles/{t.id}/play", headers=_ph(pa))).json()["resume_at_sec"] == 100
    assert (await client.get(f"/v1/titles/{t.id}/play", headers=_ph(pb))).json()["resume_at_sec"] == 200
    # No header → legacy scope, which has no progress rows.
    assert (await client.get(f"/v1/titles/{t.id}/play")).json()["resume_at_sec"] is None
