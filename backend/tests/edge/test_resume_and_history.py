"""Resume position in /play + full viewing history endpoint."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_play_returns_resume_position_after_progress(
    auth_client, make_title, make_plan, make_active_subscription
) -> None:
    """After the user posts progress, the next /play returns resume_at_sec."""
    client, _, user = auth_client
    plan = await make_plan(code="monthly")
    await make_active_subscription(user_id=user.id, plan_id=plan.id)
    t = await make_title(slug="m", hls_url="https://test.example/m.m3u8")

    # First play — no prior progress
    first = await client.get(f"/v1/titles/{t.id}/play")
    assert first.status_code == 200
    assert first.json()["resume_at_sec"] is None

    # Post progress
    await client.post(f"/v1/titles/{t.id}/progress", json={"position_sec": 450, "total_sec": 5400})

    # Second play — resume hint returned
    second = await client.get(f"/v1/titles/{t.id}/play")
    body = second.json()
    assert body["resume_at_sec"] == 450
    assert body["total_sec"] == 5400


@pytest.mark.asyncio
async def test_play_returns_episode_resume(
    auth_client, make_series_with_episodes, make_plan, make_active_subscription
) -> None:
    client, _, user = auth_client
    plan = await make_plan(code="monthly")
    await make_active_subscription(user_id=user.id, plan_id=plan.id)
    s = await make_series_with_episodes(slug="show", seasons=1, episodes_per_season=2)
    detail = (await client.get(f"/v1/titles/{s.id}/seasons/1")).json()
    e1 = detail["episodes"][0]["id"]

    await client.post(f"/v1/episodes/{e1}/progress", json={"position_sec": 700, "total_sec": 2400})
    play = await client.get(f"/v1/episodes/{e1}/play")
    body = play.json()
    assert body["resume_at_sec"] == 700
    assert body["total_sec"] == 2400


@pytest.mark.asyncio
async def test_full_history_includes_finished_titles(auth_client, make_title) -> None:
    """/me/history shows ALL titles touched, including completed ones (unlike continue-watching)."""
    client, _, _ = auth_client
    finished = await make_title(slug="finished")
    in_progress = await make_title(slug="in-progress")

    # Mark finished (>90%) and in-progress separately
    await client.post(
        f"/v1/titles/{finished.id}/progress", json={"position_sec": 990, "total_sec": 1000}
    )
    await client.post(
        f"/v1/titles/{in_progress.id}/progress", json={"position_sec": 300, "total_sec": 1000}
    )

    # Continue Watching = only the in-progress one (finished is filtered out)
    cw = await client.get("/v1/me/continue-watching")
    cw_slugs = [i["title"]["slug"] for i in cw.json()["items"]]
    assert "finished" not in cw_slugs
    assert "in-progress" in cw_slugs

    # Full History = both
    hist = await client.get("/v1/me/history")
    body = hist.json()
    h_slugs = [i["title"]["slug"] for i in body["items"]]
    assert "finished" in h_slugs
    assert "in-progress" in h_slugs
    assert body["total"] == 2


@pytest.mark.asyncio
async def test_history_pagination(auth_client, make_title) -> None:
    client, _, _ = auth_client
    for i in range(5):
        t = await make_title(slug=f"t-{i}")
        await client.post(f"/v1/titles/{t.id}/progress", json={"position_sec": 50, "total_sec": 1000})

    page1 = await client.get("/v1/me/history", params={"page": 1, "page_size": 2})
    assert page1.json()["total"] == 5
    assert len(page1.json()["items"]) == 2

    page3 = await client.get("/v1/me/history", params={"page": 3, "page_size": 2})
    assert len(page3.json()["items"]) == 1


@pytest.mark.asyncio
async def test_history_includes_hidden_from_continue(auth_client, make_title) -> None:
    """A title soft-hidden from Continue Watching STILL appears in full history."""
    client, _, _ = auth_client
    t = await make_title(slug="hidden")
    await client.post(f"/v1/titles/{t.id}/progress", json={"position_sec": 100, "total_sec": 1000})
    # Soft-hide from continue
    await client.delete(f"/v1/me/continue-watching/{t.id}")

    cw = await client.get("/v1/me/continue-watching")
    assert cw.json()["items"] == []

    hist = await client.get("/v1/me/history")
    items = hist.json()["items"]
    assert len(items) == 1
    assert items[0]["title"]["slug"] == "hidden"
    assert items[0]["hidden_from_continue"] is True


@pytest.mark.asyncio
async def test_delete_history_hard_deletes(auth_client, make_title) -> None:
    """DELETE /v1/me/history/{id} truly removes the row, unlike continue-watching soft-hide."""
    client, _, _ = auth_client
    t = await make_title(slug="x")
    await client.post(f"/v1/titles/{t.id}/progress", json={"position_sec": 100, "total_sec": 1000})

    r = await client.delete(f"/v1/me/history/{t.id}")
    assert r.status_code == 204

    hist = await client.get("/v1/me/history")
    assert hist.json()["items"] == []

    # If the user posts progress later, it's a brand-new row starting from 0
    await client.post(f"/v1/titles/{t.id}/progress", json={"position_sec": 50, "total_sec": 1000})
    hist2 = await client.get("/v1/me/history")
    assert hist2.json()["items"][0]["position_sec"] == 50
