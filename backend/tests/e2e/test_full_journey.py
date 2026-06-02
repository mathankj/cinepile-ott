"""
End-to-end V1.5 journey:
  signup → subscribe → browse home → search → detail movie → detail series →
  add to my-list → react → progress on a movie → progress on a series episode →
  continue-watching shows both → logout
"""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_full_v15_user_journey(
    client, make_plan, make_title, make_series_with_episodes
) -> None:
    # Seed catalog + plan
    await make_plan(code="monthly")
    movie = await make_title(slug="bbb", title="Big Buck Bunny", genres=["animation"])
    series = await make_series_with_episodes(
        slug="the-show", seasons=2, episodes_per_season=3, genres=["drama"]
    )

    # 1) Sign up
    signup = await client.post(
        "/v1/auth/signup",
        json={"email": "u@example.com", "password": "supersecret9", "full_name": "U"},
    )
    assert signup.status_code == 201
    tokens = signup.json()["tokens"]
    client.headers["Authorization"] = f"Bearer {tokens['access_token']}"

    # 2) Subscribe
    sub = await client.post("/v1/subscriptions", json={"plan_code": "monthly"})
    assert sub.status_code == 201

    # 3) Browse home (anonymous-able + personalised rows when authed)
    home = await client.get("/v1/home")
    assert home.status_code == 200
    kinds = [r["kind"] for r in home.json()["rows"]]
    assert "new_releases" in kinds

    # 4) Search
    found = await client.get("/v1/titles/search", params={"q": "bunny"})
    assert any(t["slug"] == "bbb" for t in found.json())

    # 5) Movie detail + play
    movie_detail = await client.get(f"/v1/titles/{movie.id}")
    assert movie_detail.status_code == 200 and movie_detail.json()["type"] == "movie"
    play_movie = await client.get(f"/v1/titles/{movie.id}/play")
    assert play_movie.status_code == 200

    # 6) Series detail + season + episode play
    series_detail = await client.get(f"/v1/titles/{series.id}")
    assert series_detail.json()["type"] == "series"
    assert len(series_detail.json()["seasons"]) == 2

    season1 = await client.get(f"/v1/titles/{series.id}/seasons/1")
    ep1 = season1.json()["episodes"][0]
    play_ep = await client.get(f"/v1/episodes/{ep1['id']}/play")
    assert play_ep.status_code == 200

    # 7) Add to My List + react
    add = await client.post(f"/v1/me/list/{movie.id}")
    assert add.json()["added"] is True
    react = await client.put(f"/v1/titles/{movie.id}/reaction", json={"kind": "double_thumbs_up"})
    assert react.status_code == 200

    # 8) Progress on movie + episode
    await client.post(f"/v1/titles/{movie.id}/progress", json={"position_sec": 300, "total_sec": 600})
    await client.post(f"/v1/episodes/{ep1['id']}/progress", json={"position_sec": 800, "total_sec": 2400})

    # 9) Continue-watching shows both (series collapsed)
    cw = (await client.get("/v1/me/continue-watching")).json()
    title_ids_in_cw = {i["title"]["id"] for i in cw["items"]}
    assert movie.id in title_ids_in_cw
    assert series.id in title_ids_in_cw

    # 10) My-list contains the movie
    my = (await client.get("/v1/me/list")).json()
    assert any(i["title"]["id"] == movie.id for i in my["items"])

    # 11) Personalised home rows now include continue_watching + my_list
    home2 = (await client.get("/v1/home")).json()
    kinds2 = [r["kind"] for r in home2["rows"]]
    assert "continue_watching" in kinds2
    assert "my_list" in kinds2

    # 12) Logout
    out = await client.post("/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]})
    assert out.status_code == 204
