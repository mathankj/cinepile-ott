"""Empty-state handling on /v1/home."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_anonymous_home_with_no_catalog(client) -> None:
    """Bare backend, no titles seeded — home must return 200 with empty rows."""
    resp = await client.get("/v1/home")
    assert resp.status_code == 200
    body = resp.json()
    # New Releases + Trending rows exist but are empty
    kinds = [r["kind"] for r in body["rows"]]
    assert "new_releases" in kinds or "trending_now" in kinds
    for r in body["rows"]:
        assert isinstance(r["items"], list)


@pytest.mark.asyncio
async def test_authed_home_with_zero_history(auth_client) -> None:
    """A new user with zero history must NOT see continue_watching or my_list rows.
    Those rows are hidden when empty (don't show empty placeholders mid-feed)."""
    client, _, _ = auth_client
    resp = await client.get("/v1/home")
    assert resp.status_code == 200
    kinds = [r["kind"] for r in resp.json()["rows"]]
    assert "continue_watching" not in kinds
    assert "my_list" not in kinds


@pytest.mark.asyncio
async def test_home_includes_continue_watching_when_present(auth_client, make_title) -> None:
    client, _, _ = auth_client
    title = await make_title(slug="m")
    await client.post(f"/v1/titles/{title.id}/progress", json={"position_sec": 100, "total_sec": 1000})

    resp = await client.get("/v1/home")
    kinds = [r["kind"] for r in resp.json()["rows"]]
    assert "continue_watching" in kinds
