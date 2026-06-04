"""Upload size + content-type validation tests (C5, C6)."""
from __future__ import annotations

import io

import pytest


# Valid ISO BMFF (MP4) ftyp box header — 32 bytes. The upload validator sniffs
# bytes 4-8 for `ftyp`; without this prefix any test would 415 on content-mismatch
# before reaching the actual code path under test.
_FTYP = (
    b"\x00\x00\x00\x20"
    b"ftyp"
    b"isom\x00\x00\x02\x00"
    b"isomiso2avc1mp41"
)


@pytest.mark.asyncio
async def test_upload_rejects_oversize_file(
    storage_mock_private, admin_client, make_title, monkeypatch
) -> None:
    """C5 — set the limit to 1 KB in this test and try to upload 10 KB."""
    # Bring the limit down for the test
    from app.api.v1 import admin as admin_mod

    monkeypatch.setattr(admin_mod, "_MAX_UPLOAD_BYTES", 1024)  # 1 KB

    client, _, _ = admin_client
    t = await make_title(slug="m", hls_url=None)
    big = io.BytesIO(_FTYP + b"x" * 10_000)  # 10 KB > 1 KB limit
    resp = await client.post(
        f"/v1/admin/titles/{t.id}/upload-video",
        files={"file": ("big.mp4", big, "video/mp4")},
    )
    assert resp.status_code == 413
    assert resp.json()["detail"]["error"]["code"] == "payload_too_large"


@pytest.mark.asyncio
async def test_upload_rejects_wrong_extension(
    storage_mock_private, admin_client, make_title
) -> None:
    """C6 — uploads must have an allowed video extension."""
    client, _, _ = admin_client
    t = await make_title(slug="m", hls_url=None)
    fake = io.BytesIO(b"not a real exe")
    resp = await client.post(
        f"/v1/admin/titles/{t.id}/upload-video",
        files={"file": ("virus.exe", fake, "application/octet-stream")},
    )
    assert resp.status_code == 415
    assert resp.json()["detail"]["error"]["code"] == "unsupported_media"


@pytest.mark.asyncio
async def test_upload_rejects_wrong_mime(
    storage_mock_private, admin_client, make_title
) -> None:
    """C6 — content-type must be in the whitelist."""
    client, _, _ = admin_client
    t = await make_title(slug="m", hls_url=None)
    fake = io.BytesIO(b"x" * 100)
    resp = await client.post(
        f"/v1/admin/titles/{t.id}/upload-video",
        files={"file": ("x.mp4", fake, "text/html")},  # mp4 ext but html mime
    )
    assert resp.status_code == 415


@pytest.mark.asyncio
async def test_upload_accepts_mp4(storage_mock_private, admin_client, make_title) -> None:
    """Sanity — valid uploads still work."""
    client, _, _ = admin_client
    t = await make_title(slug="m", hls_url=None)
    fake = io.BytesIO(_FTYP + b"x" * 100)
    resp = await client.post(
        f"/v1/admin/titles/{t.id}/upload-video",
        files={"file": ("real.mp4", fake, "video/mp4")},
    )
    assert resp.status_code == 200
