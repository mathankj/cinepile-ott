"""Admin video upload endpoints (movie + episode) against mocked S3-compatible storage."""
from __future__ import annotations

import io

import pytest


@pytest.mark.asyncio
async def test_upload_disabled_when_storage_unconfigured(admin_client, make_title) -> None:
    """Without STORAGE_* env vars, uploads return 503 instead of crashing."""
    client, _, _ = admin_client
    t = await make_title(slug="m")
    fake_mp4 = io.BytesIO(b"fakebytes" * 100)
    resp = await client.post(
        f"/v1/admin/titles/{t.id}/upload-video",
        files={"file": ("test.mp4", fake_mp4, "video/mp4")},
    )
    assert resp.status_code == 503
    assert resp.json()["detail"]["error"]["code"] == "storage_not_configured"


# ---- Public bucket mode ------------------------------------------------------


@pytest.mark.asyncio
async def test_upload_title_public_returns_url(storage_mock, admin_client, make_title) -> None:
    client, _, _ = admin_client
    t = await make_title(slug="m", hls_url=None)
    fake_mp4 = io.BytesIO(b"fakebytes" * 500)
    resp = await client.post(
        f"/v1/admin/titles/{t.id}/upload-video",
        files={"file": ("bunny.mp4", fake_mp4, "video/mp4")},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # Public mode: stored_ref IS the full URL
    assert body["stored_ref"].startswith("https://pub-test.r2.dev/")
    assert body["playable_url"] == body["stored_ref"]

    detail = await client.get(f"/v1/titles/{t.id}")
    assert any(
        a["kind"] == "hls_manifest" and a["storage_url"].startswith("https://pub-test.r2.dev/")
        for a in detail.json()["assets"]
    )


# ---- Private bucket mode (B2 in dev) -----------------------------------------


@pytest.mark.asyncio
async def test_upload_title_private_stores_key_not_url(
    storage_mock_private, admin_client, make_title
) -> None:
    client, _, _ = admin_client
    t = await make_title(slug="m", hls_url=None)
    fake_mp4 = io.BytesIO(b"fakebytes" * 500)
    resp = await client.post(
        f"/v1/admin/titles/{t.id}/upload-video",
        files={"file": ("bunny.mp4", fake_mp4, "video/mp4")},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # Private mode: stored_ref is the bucket KEY, not a URL
    assert body["stored_ref"] == f"titles/{t.id}/master.mp4"
    # playable_url is a fresh presigned URL with AWSAccessKeyId / Signature query params
    assert body["playable_url"].startswith("https://s3.us-east-1.amazonaws.com/")
    assert "Signature" in body["playable_url"] or "X-Amz-Signature" in body["playable_url"]


@pytest.mark.asyncio
async def test_play_private_uploaded_movie_gets_signed_url(
    storage_mock_private,
    client,
    make_user,
    make_title,
    make_plan,
    make_active_subscription,
) -> None:
    """Full flow: admin uploads to private bucket → user plays → gets a signed URL.

    Uses bare `client` fixture (no auth) so we can switch Authorization headers
    between admin and user explicitly. The auth_client + admin_client fixtures
    share the same client.headers and would collide.
    """
    admin = await make_user(email="admin@x.com", password="password123", role="admin")
    user = await make_user(email="user@x.com", password="password123")
    plan = await make_plan(code="monthly")
    await make_active_subscription(user_id=user.id, plan_id=plan.id)
    t = await make_title(slug="priv", hls_url=None)

    # Login as admin and upload
    admin_login = await client.post(
        "/v1/auth/login", json={"email": "admin@x.com", "password": "password123"}
    )
    client.headers["Authorization"] = f"Bearer {admin_login.json()['tokens']['access_token']}"
    fake = io.BytesIO(b"x" * 100)
    upload_resp = await client.post(
        f"/v1/admin/titles/{t.id}/upload-video",
        files={"file": ("x.mp4", fake, "video/mp4")},
    )
    assert upload_resp.status_code == 200, upload_resp.text

    # Switch to subscribed user and play
    user_login = await client.post(
        "/v1/auth/login", json={"email": "user@x.com", "password": "password123"}
    )
    client.headers["Authorization"] = f"Bearer {user_login.json()['tokens']['access_token']}"

    play = await client.get(f"/v1/titles/{t.id}/play")
    assert play.status_code == 200, play.text
    body = play.json()
    # Manifest URL must be a presigned URL (not the bucket key)
    assert body["manifest_url"].startswith("https://s3.us-east-1.amazonaws.com/")
    assert "Signature" in body["manifest_url"] or "X-Amz-Signature" in body["manifest_url"]


# ---- Behaviour regardless of mode --------------------------------------------


@pytest.mark.asyncio
async def test_upload_replaces_existing_asset(storage_mock, admin_client, make_title) -> None:
    client, _, _ = admin_client
    t = await make_title(slug="m", hls_url="https://old.example/old.m3u8")

    fake_mp4 = io.BytesIO(b"newbytes" * 200)
    resp = await client.post(
        f"/v1/admin/titles/{t.id}/upload-video",
        files={"file": ("new.mp4", fake_mp4, "video/mp4")},
    )
    assert resp.status_code == 200

    detail = await client.get(f"/v1/titles/{t.id}")
    hls_assets = [a for a in detail.json()["assets"] if a["kind"] == "hls_manifest"]
    assert len(hls_assets) == 1  # not 2
    assert "pub-test.r2.dev" in hls_assets[0]["storage_url"]


@pytest.mark.asyncio
async def test_upload_rejects_for_series_title(
    storage_mock, admin_client, make_series_with_episodes
) -> None:
    client, _, _ = admin_client
    s = await make_series_with_episodes(slug="show", seasons=1, episodes_per_season=1)
    fake = io.BytesIO(b"x" * 100)
    resp = await client.post(
        f"/v1/admin/titles/{s.id}/upload-video",
        files={"file": ("x.mp4", fake, "video/mp4")},
    )
    assert resp.status_code == 409
    assert resp.json()["detail"]["error"]["code"] == "type_mismatch"


@pytest.mark.asyncio
async def test_upload_episode_video(storage_mock, admin_client, make_series_with_episodes) -> None:
    client, _, _ = admin_client
    s = await make_series_with_episodes(slug="show", seasons=1, episodes_per_season=2)
    season = (await client.get(f"/v1/titles/{s.id}/seasons/1")).json()
    ep_id = season["episodes"][0]["id"]

    fake = io.BytesIO(b"epbytes" * 300)
    resp = await client.post(
        f"/v1/admin/episodes/{ep_id}/upload-video",
        files={"file": ("s1e1.mp4", fake, "video/mp4")},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["episode_id"] == ep_id
    assert resp.json()["key"] == f"episodes/{ep_id}/master.mp4"


@pytest.mark.asyncio
async def test_upload_requires_content_role(storage_mock, auth_client, make_title) -> None:
    client, _, _ = auth_client
    t = await make_title(slug="m")
    fake = io.BytesIO(b"x")
    resp = await client.post(
        f"/v1/admin/titles/{t.id}/upload-video", files={"file": ("x.mp4", fake, "video/mp4")}
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_upload_writes_audit_log(storage_mock, admin_client, make_title) -> None:
    client, _, _ = admin_client
    t = await make_title(slug="m", hls_url=None)
    fake = io.BytesIO(b"x" * 100)
    await client.post(
        f"/v1/admin/titles/{t.id}/upload-video", files={"file": ("x.mp4", fake, "video/mp4")}
    )
    audit = await client.get("/v1/admin/audit", params={"entity_type": "title", "entity_id": t.id})
    actions = [e["action"] for e in audit.json()["items"]]
    assert "title.upload_video" in actions
