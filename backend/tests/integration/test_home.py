"""GET /v1/home — browse rows."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_home_anonymous(client, make_title) -> None:
    await make_title(slug="m1")
    await make_title(slug="m2")
    resp = await client.get("/v1/home")
    assert resp.status_code == 200
    rows = resp.json()["rows"]
    kinds = [r["kind"] for r in rows]
    # Anonymous: must NOT include personalised rows
    assert "continue_watching" not in kinds
    assert "my_list" not in kinds
    assert "new_releases" in kinds
    assert "trending_now" in kinds


@pytest.mark.asyncio
async def test_home_authed_personalised(auth_client, make_title) -> None:
    client, _, _ = auth_client
    t = await make_title(slug="m1")
    await client.post(f"/v1/me/list/{t.id}")
    await client.post(f"/v1/titles/{t.id}/progress", json={"position_sec": 100, "total_sec": 1000})

    rows = (await client.get("/v1/home")).json()["rows"]
    kinds = [r["kind"] for r in rows]
    assert "continue_watching" in kinds
    assert "my_list" in kinds


@pytest.mark.asyncio
async def test_home_top_in_country(auth_client, make_title, make_plan, make_active_subscription) -> None:
    client, _, user = auth_client
    plan = await make_plan(code="monthly")
    await make_active_subscription(user_id=user.id, plan_id=plan.id)
    t_in = await make_title(slug="in-1", countries=["IN"], hls_url="https://x/m.m3u8")
    await make_title(slug="us-1", countries=["US"])

    # Bump view count by playing
    await client.get(f"/v1/titles/{t_in.id}/play")

    resp = await client.get("/v1/home", params={"country": "IN"})
    rows = resp.json()["rows"]
    top = next((r for r in rows if r["kind"] == "top_in_country"), None)
    assert top is not None
    assert any(i["slug"] == "in-1" for i in top["items"])


@pytest.mark.asyncio
async def test_home_because_you_watched(
    auth_client, make_title, make_plan, make_active_subscription, db_session
) -> None:
    """Finishing a title triggers a Because-You-Watched row of same-genre titles."""
    client, _, user = auth_client
    plan = await make_plan(code="monthly")
    await make_active_subscription(user_id=user.id, plan_id=plan.id)

    seed = await make_title(slug="seed", genres=["action"])
    sibling = await make_title(slug="sibling", genres=["action"])
    unrelated = await make_title(slug="unrelated", genres=["drama"])

    # Finish the seed by hitting >90% progress
    await client.post(
        f"/v1/titles/{seed.id}/progress", json={"position_sec": 990, "total_sec": 1000}
    )

    rows = (await client.get("/v1/home")).json()["rows"]
    byw = next((r for r in rows if r["kind"].startswith("because_you_watched:")), None)
    assert byw is not None
    slugs = {i["slug"] for i in byw["items"]}
    assert "sibling" in slugs
    assert "unrelated" not in slugs
    assert "seed" not in slugs  # seed excluded
