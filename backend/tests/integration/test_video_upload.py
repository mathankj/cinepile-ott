"""Admin video upload endpoints (movie + episode) against mocked R2."""
from __future__ import annotations

import io

import pytest


@pytest.mark.asyncio
async def test_upload_disabled_when_r2_unconfigured(admin_client, make_title) -> None:
    """Without R2 env vars, uploads return 503 instead of crashing."""
    client, _, _ = admin_client
    t = await make_title(slug="m")
    fake_mp4 = io.BytesIO(b"fakebytes" * 100)
    resp = await client.post(
        f"/v1/admin/titles/{t.id}/upload-video",
        files={"file": ("test.mp4", fake_mp4, "video/mp4")},
    )
    assert resp.status_code == 503
    assert resp.json()["detail"]["error"]["code"] == "storage_not_configured"


@pytest.mark.asyncio
async def test_upload_title_video_happy_path(r2_mock, admin_client, make_title) -> None:
    client, _, _ = admin_client
    t = await make_title(slug="m", hls_url=None)  # no existing asset
    fake_mp4 = io.BytesIO(b"fakebytes" * 500)
    resp = await client.post(
        f"/v1/admin/titles/{t.id}/upload-video",
        files={"file": ("bunny.mp4", fake_mp4, "video/mp4")},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["title_id"] == t.id
    assert body["key"] == f"titles/{t.id}/master.mp4"
    assert body["url"].startswith("https://pub-test.r2.dev/")

    # Title detail now shows the asset
    detail = await client.get(f"/v1/titles/{t.id}")
    assets = detail.json()["assets"]
    assert any(a["kind"] == "hls_manifest" and "pub-test.r2.dev" in a["storage_url"] for a in assets)


@pytest.mark.asyncio
async def test_upload_replaces_existing_asset(r2_mock, admin_client, make_title) -> None:
    """Re-uploading replaces the prior hls_manifest pointer (not duplicate rows)."""
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
    r2_mock, admin_client, make_series_with_episodes
) -> None:
    """Series upload must go to the episode endpoint, not the title endpoint."""
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
async def test_upload_episode_video(r2_mock, admin_client, make_series_with_episodes) -> None:
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
    body = resp.json()
    assert body["episode_id"] == ep_id
    assert body["key"] == f"episodes/{ep_id}/master.mp4"


@pytest.mark.asyncio
async def test_upload_requires_content_role(r2_mock, auth_client, make_title) -> None:
    """Regular users cannot upload."""
    client, _, _ = auth_client
    t = await make_title(slug="m")
    fake = io.BytesIO(b"x")
    resp = await client.post(
        f"/v1/admin/titles/{t.id}/upload-video", files={"file": ("x.mp4", fake, "video/mp4")}
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_upload_writes_audit_log(r2_mock, admin_client, make_title) -> None:
    client, _, _ = admin_client
    t = await make_title(slug="m", hls_url=None)
    fake = io.BytesIO(b"x" * 100)
    await client.post(
        f"/v1/admin/titles/{t.id}/upload-video", files={"file": ("x.mp4", fake, "video/mp4")}
    )

    audit = await client.get("/v1/admin/audit", params={"entity_type": "title", "entity_id": t.id})
    actions = [e["action"] for e in audit.json()["items"]]
    assert "title.upload_video" in actions
