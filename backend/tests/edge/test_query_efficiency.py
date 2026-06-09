"""Query-count regression tests.

The Title model eager-loads 7 relationships via lazy="selectin", which is
right for the detail page but disastrous for row/list queries: every list
SELECT used to fan out into ~8 extra SELECTs even though TitleSummary only
needs scalar columns. These tests pin the per-request statement counts so a
future relationship addition (or a dropped noload()) shows up as a failure
here instead of as a slow home page in production.
"""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine


@contextmanager
def count_selects(engine: AsyncEngine) -> Iterator[list[str]]:
    """Collects every SELECT statement executed on the engine while active.

    We count only SELECTs (not BEGIN/UPDATE/INSERT) because the selectin
    fan-out we're guarding against manifests purely as extra SELECTs.
    """
    statements: list[str] = []

    def _on_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append(statement)

    event.listen(engine.sync_engine, "before_cursor_execute", _on_cursor_execute)
    try:
        yield statements
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", _on_cursor_execute)


@pytest.mark.asyncio
async def test_home_anonymous_is_two_selects(client, db_engine, make_title) -> None:
    """Anonymous /v1/home builds exactly 2 rows (new_releases + trending), so a
    cold cache build should run exactly 2 SELECTs — one per row. Before the
    noload() fix this was 16 (each row query triggered 7 selectin loads)."""
    for i in range(5):
        await make_title(slug=f"qe-home-{i}", genres=["drama"])

    with count_selects(db_engine) as stmts:
        resp = await client.get("/v1/home")
    assert resp.status_code == 200
    assert len(resp.json()["rows"]) == 2
    assert len(stmts) <= 2, f"home fan-out regression: {len(stmts)} SELECTs:\n" + "\n---\n".join(stmts)


@pytest.mark.asyncio
async def test_home_second_request_hits_cache(client, db_engine, make_title) -> None:
    """The /v1/home TTL cache must absorb repeat requests entirely."""
    await make_title(slug="qe-cached", genres=["drama"])

    first = await client.get("/v1/home")
    assert first.status_code == 200
    with count_selects(db_engine) as stmts:
        resp = await client.get("/v1/home")
    assert resp.status_code == 200
    assert len(stmts) == 0, "cached /v1/home should not touch the database"


@pytest.mark.asyncio
async def test_titles_list_is_two_selects(client, db_engine, make_title) -> None:
    """/v1/titles needs exactly 2 SELECTs: the page query + the COUNT.
    Before the noload() fix it was 9."""
    for i in range(5):
        await make_title(slug=f"qe-list-{i}", genres=["drama"])

    with count_selects(db_engine) as stmts:
        resp = await client.get("/v1/titles")
    assert resp.status_code == 200
    assert len(stmts) <= 2, f"list fan-out regression: {len(stmts)} SELECTs:\n" + "\n---\n".join(stmts)


@pytest.mark.asyncio
async def test_title_detail_keeps_eager_loading(client, make_title) -> None:
    """The detail path must STILL eager-load relationships — noload() is for
    row/list queries only. Genres present in the response proves selectin
    loading survived on the detail path."""
    t = await make_title(slug="qe-detail", genres=["drama", "thriller"])
    resp = await client.get(f"/v1/titles/{t.id}")
    assert resp.status_code == 200
    assert {g["slug"] for g in resp.json()["genres"]} == {"drama", "thriller"}
