"""Admin features wave 1: title restore, deleted-titles list, admin season
view, genre update/delete, last-admin protection."""
from __future__ import annotations

import pytest


# ---- Helpers -------------------------------------------------------------------


async def _create_title(client, slug: str, *, type_: str = "movie", status: str = "published") -> int:
    resp = await client.post(
        "/v1/admin/titles",
        json={"slug": slug, "type": type_, "title": slug.title(), "status": status},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _create_genre(client, slug: str, *, kind: str = "primary") -> int:
    resp = await client.post(
        "/v1/admin/genres", json={"slug": slug, "name": slug.title(), "kind": kind}
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


# ---- POST /v1/admin/titles/{id}/restore ------------------------------------------


@pytest.mark.asyncio
async def test_restore_soft_deleted_title(admin_client) -> None:
    client, _, _ = admin_client
    tid = await _create_title(client, "restore-me")

    assert (await client.delete(f"/v1/admin/titles/{tid}")).status_code == 204
    # soft-deleted → even the admin detail endpoint 404s
    assert (await client.get(f"/v1/admin/titles/{tid}")).status_code == 404

    resp = await client.post(f"/v1/admin/titles/{tid}/restore")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # soft-delete forced status='removed'; restore lands in the safe
    # non-public 'archived' state instead of surprise-publishing
    assert body["status"] == "archived"

    # back in the admin editor...
    assert (await client.get(f"/v1/admin/titles/{tid}")).status_code == 200
    # ...but still hidden from the public catalog
    assert (await client.get(f"/v1/titles/{tid}")).status_code == 404


@pytest.mark.asyncio
async def test_restore_writes_audit_entry(admin_client) -> None:
    client, _, _ = admin_client
    tid = await _create_title(client, "restore-audited")
    await client.delete(f"/v1/admin/titles/{tid}")
    await client.post(f"/v1/admin/titles/{tid}/restore")

    audit = await client.get("/v1/admin/audit", params={"entity_type": "title", "entity_id": tid})
    entries = {e["action"]: e for e in audit.json()["items"]}
    assert "title.restore" in entries
    entry = entries["title.restore"]
    assert entry["before"]["status"] == "removed"
    assert entry["after"]["status"] == "archived"


@pytest.mark.asyncio
async def test_restore_not_deleted_title_is_404(admin_client) -> None:
    client, _, _ = admin_client
    tid = await _create_title(client, "alive")
    resp = await client.post(f"/v1/admin/titles/{tid}/restore")
    assert resp.status_code == 404
    assert resp.json()["detail"]["error"]["code"] == "title_not_found"


@pytest.mark.asyncio
async def test_restore_missing_title_is_404(admin_client) -> None:
    client, _, _ = admin_client
    resp = await client.post("/v1/admin/titles/999999/restore")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_restore_forbidden_for_regular_user(auth_client) -> None:
    client, _, _ = auth_client
    resp = await client.post("/v1/admin/titles/1/restore")
    assert resp.status_code == 403


# ---- GET /v1/admin/titles-deleted -------------------------------------------------


@pytest.mark.asyncio
async def test_deleted_titles_listed_newest_first(admin_client) -> None:
    client, _, _ = admin_client
    keep = await _create_title(client, "kept")
    first = await _create_title(client, "deleted-first")
    second = await _create_title(client, "deleted-second")
    await client.delete(f"/v1/admin/titles/{first}")
    await client.delete(f"/v1/admin/titles/{second}")

    resp = await client.get("/v1/admin/titles-deleted")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # exact TitleListResponse shape — the frontend reuses its list rendering
    assert set(body.keys()) == {"items", "page", "page_size", "total"}
    assert body["total"] == 2
    ids = [i["id"] for i in body["items"]]
    assert ids == [second, first]  # newest deletion first
    assert keep not in ids


@pytest.mark.asyncio
async def test_deleted_titles_pagination(admin_client) -> None:
    client, _, _ = admin_client
    for n in range(3):
        tid = await _create_title(client, f"bulk-{n}")
        await client.delete(f"/v1/admin/titles/{tid}")

    page1 = (await client.get("/v1/admin/titles-deleted", params={"page": 1, "page_size": 2})).json()
    page2 = (await client.get("/v1/admin/titles-deleted", params={"page": 2, "page_size": 2})).json()
    assert page1["total"] == 3 and page2["total"] == 3
    assert len(page1["items"]) == 2
    assert len(page2["items"]) == 1
    assert {i["id"] for i in page1["items"]}.isdisjoint({i["id"] for i in page2["items"]})


@pytest.mark.asyncio
async def test_restored_title_leaves_deleted_list(admin_client) -> None:
    client, _, _ = admin_client
    tid = await _create_title(client, "round-trip")
    await client.delete(f"/v1/admin/titles/{tid}")
    await client.post(f"/v1/admin/titles/{tid}/restore")

    body = (await client.get("/v1/admin/titles-deleted")).json()
    assert tid not in [i["id"] for i in body["items"]]
    assert body["total"] == 0


@pytest.mark.asyncio
async def test_deleted_titles_forbidden_for_regular_user(auth_client) -> None:
    client, _, _ = auth_client
    resp = await client.get("/v1/admin/titles-deleted")
    assert resp.status_code == 403


# ---- GET /v1/admin/titles/{id}/seasons --------------------------------------------


@pytest.mark.asyncio
async def test_admin_seasons_include_drafts(admin_client) -> None:
    client, _, _ = admin_client
    series_id = await _create_title(client, "admin-show", type_="series")
    s1 = (await client.post(
        f"/v1/admin/titles/{series_id}/seasons", json={"season_number": 1, "name": "S1"}
    )).json()["id"]
    # one published + one draft episode — the draft is the point of this endpoint
    await client.post(
        f"/v1/admin/seasons/{s1}/episodes",
        json={"episode_number": 1, "name": "Published Ep", "status": "published"},
    )
    await client.post(
        f"/v1/admin/seasons/{s1}/episodes",
        json={"episode_number": 2, "name": "Draft Ep", "status": "draft"},
    )
    # empty second season must still appear
    await client.post(f"/v1/admin/titles/{series_id}/seasons", json={"season_number": 2})

    resp = await client.get(f"/v1/admin/titles/{series_id}/seasons")
    assert resp.status_code == 200, resp.text
    seasons = resp.json()
    assert [s["season_number"] for s in seasons] == [1, 2]
    statuses = {e["status"] for e in seasons[0]["episodes"]}
    assert statuses == {"published", "draft"}
    assert seasons[1]["episodes"] == []


@pytest.mark.asyncio
async def test_admin_seasons_on_movie_is_type_mismatch(admin_client) -> None:
    client, _, _ = admin_client
    tid = await _create_title(client, "just-a-movie", type_="movie")
    resp = await client.get(f"/v1/admin/titles/{tid}/seasons")
    assert resp.status_code == 409
    assert resp.json()["detail"]["error"]["code"] == "type_mismatch"


@pytest.mark.asyncio
async def test_admin_seasons_missing_title_is_404(admin_client) -> None:
    client, _, _ = admin_client
    resp = await client.get("/v1/admin/titles/999999/seasons")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_admin_seasons_forbidden_for_regular_user(auth_client) -> None:
    client, _, _ = auth_client
    resp = await client.get("/v1/admin/titles/1/seasons")
    assert resp.status_code == 403


# ---- PATCH /v1/admin/genres/{id} ---------------------------------------------------


@pytest.mark.asyncio
async def test_update_genre_fields(admin_client) -> None:
    client, _, _ = admin_client
    gid = await _create_genre(client, "dramedy")

    resp = await client.patch(
        f"/v1/admin/genres/{gid}", json={"name": "Dramedy & Friends", "kind": "mood"}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["name"] == "Dramedy & Friends"
    assert body["kind"] == "mood"
    assert body["slug"] == "dramedy"  # untouched fields stay put

    audit = await client.get("/v1/admin/audit", params={"entity_type": "genre", "entity_id": gid})
    actions = [e["action"] for e in audit.json()["items"]]
    assert "genre.update" in actions


@pytest.mark.asyncio
async def test_update_genre_slug_collision_is_409(admin_client) -> None:
    client, _, _ = admin_client
    await _create_genre(client, "action")
    gid = await _create_genre(client, "thriller")

    resp = await client.patch(f"/v1/admin/genres/{gid}", json={"slug": "action"})
    assert resp.status_code == 409
    assert resp.json()["detail"]["error"]["code"] == "genre_slug_in_use"


@pytest.mark.asyncio
async def test_update_genre_own_slug_is_not_a_collision(admin_client) -> None:
    client, _, _ = admin_client
    gid = await _create_genre(client, "comedy")
    # re-sending the current slug must be a no-op, not a 409
    resp = await client.patch(f"/v1/admin/genres/{gid}", json={"slug": "comedy", "name": "Comedy!"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Comedy!"


@pytest.mark.asyncio
async def test_update_genre_rejects_unknown_field(admin_client) -> None:
    client, _, _ = admin_client
    gid = await _create_genre(client, "horror")
    resp = await client.patch(f"/v1/admin/genres/{gid}", json={"id": 999})
    assert resp.status_code == 422  # extra='forbid'


@pytest.mark.asyncio
async def test_update_missing_genre_is_404(admin_client) -> None:
    client, _, _ = admin_client
    resp = await client.patch("/v1/admin/genres/999999", json={"name": "Ghost"})
    assert resp.status_code == 404
    assert resp.json()["detail"]["error"]["code"] == "genre_not_found"


@pytest.mark.asyncio
async def test_genre_update_allowed_for_content_manager(content_manager_client) -> None:
    """Genres are catalog writes — content_manager passes the gate."""
    client, _, _ = content_manager_client
    gid = await _create_genre(client, "romance")
    resp = await client.patch(f"/v1/admin/genres/{gid}", json={"name": "Romance"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_genre_update_forbidden_for_regular_user(auth_client) -> None:
    client, _, _ = auth_client
    resp = await client.patch("/v1/admin/genres/1", json={"name": "Nope"})
    assert resp.status_code == 403


# ---- DELETE /v1/admin/genres/{id} --------------------------------------------------


@pytest.mark.asyncio
async def test_delete_unused_genre(admin_client) -> None:
    client, _, _ = admin_client
    gid = await _create_genre(client, "disposable")

    resp = await client.delete(f"/v1/admin/genres/{gid}")
    assert resp.status_code == 204

    slugs = [g["slug"] for g in (await client.get("/v1/admin/genres")).json()]
    assert "disposable" not in slugs

    audit = await client.get("/v1/admin/audit", params={"entity_type": "genre", "entity_id": gid})
    actions = [e["action"] for e in audit.json()["items"]]
    assert "genre.delete" in actions


@pytest.mark.asyncio
async def test_delete_genre_in_use_is_409(admin_client) -> None:
    client, _, _ = admin_client
    gid = await _create_genre(client, "attached")
    title_resp = await client.post(
        "/v1/admin/titles",
        json={"slug": "uses-genre", "type": "movie", "title": "Uses Genre", "genre_slugs": ["attached"]},
    )
    assert title_resp.status_code == 201

    resp = await client.delete(f"/v1/admin/genres/{gid}")
    assert resp.status_code == 409
    assert resp.json()["detail"]["error"]["code"] == "genre_in_use"

    # detach, then deletion succeeds
    tid = title_resp.json()["id"]
    await client.patch(f"/v1/admin/titles/{tid}", json={"genre_slugs": []})
    assert (await client.delete(f"/v1/admin/genres/{gid}")).status_code == 204


@pytest.mark.asyncio
async def test_delete_missing_genre_is_404(admin_client) -> None:
    client, _, _ = admin_client
    resp = await client.delete("/v1/admin/genres/999999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_genre_delete_forbidden_for_regular_user(auth_client) -> None:
    client, _, _ = auth_client
    resp = await client.delete("/v1/admin/genres/1")
    assert resp.status_code == 403


# ---- Last-admin protection ---------------------------------------------------------


@pytest.mark.asyncio
async def test_demoting_last_admin_is_blocked(admin_client) -> None:
    client, _, admin = admin_client
    resp = await client.patch(f"/v1/admin/users/{admin.id}/role", json={"role": "user"})
    assert resp.status_code == 409
    assert resp.json()["detail"]["error"]["code"] == "last_admin"

    # the failed demotion must not have changed the role or rotated the
    # session_version — the same token still has admin access
    assert (await client.get("/v1/admin/users")).status_code == 200


@pytest.mark.asyncio
async def test_demoting_admin_allowed_when_another_admin_exists(admin_client, make_user) -> None:
    client, _, _ = admin_client
    other = await make_user(email="second-admin@example.com", role="admin")
    resp = await client.patch(f"/v1/admin/users/{other.id}/role", json={"role": "content_manager"})
    assert resp.status_code == 200
    assert resp.json()["role"] == "content_manager"


@pytest.mark.asyncio
async def test_promoting_to_admin_is_never_blocked(admin_client, make_user) -> None:
    """The guard only fires on demotion AWAY from admin."""
    client, _, _ = admin_client
    u = await make_user(email="newbie@example.com")
    resp = await client.patch(f"/v1/admin/users/{u.id}/role", json={"role": "admin"})
    assert resp.status_code == 200
    assert resp.json()["role"] == "admin"
