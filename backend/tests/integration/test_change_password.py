"""POST /v1/auth/change-password — success, failure modes, session rotation."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

EMAIL = "changer@example.com"
OLD_PASSWORD = "oldpassword123"
NEW_PASSWORD = "newpassword456"


async def _signup(client: AsyncClient) -> dict:
    resp = await client.post(
        "/v1/auth/signup",
        json={"email": EMAIL, "password": OLD_PASSWORD, "full_name": "Changer"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_change_password_success_returns_fresh_token_pair(client: AsyncClient) -> None:
    body = await _signup(client)
    old_access = body["tokens"]["access_token"]

    resp = await client.post(
        "/v1/auth/change-password",
        json={"current_password": OLD_PASSWORD, "new_password": NEW_PASSWORD},
        headers=_auth(old_access),
    )
    assert resp.status_code == 200, resp.text
    pair = resp.json()
    assert pair["access_token"]
    assert pair["refresh_token"]
    assert pair["token_type"] == "bearer"

    # The fresh access token keeps the caller logged in (carries the bumped
    # session_version)...
    me = await client.get("/v1/auth/me", headers=_auth(pair["access_token"]))
    assert me.status_code == 200
    assert me.json()["email"] == EMAIL

    # ...while the OLD access token is dead (session_version bump).
    me_old = await client.get("/v1/auth/me", headers=_auth(old_access))
    assert me_old.status_code == 401

    # New password works, old one doesn't.
    ok = await client.post("/v1/auth/login", json={"email": EMAIL, "password": NEW_PASSWORD})
    assert ok.status_code == 200
    bad = await client.post("/v1/auth/login", json={"email": EMAIL, "password": OLD_PASSWORD})
    assert bad.status_code == 401


@pytest.mark.asyncio
async def test_change_password_revokes_old_refresh_tokens(client: AsyncClient) -> None:
    body = await _signup(client)
    old_access = body["tokens"]["access_token"]
    old_refresh = body["tokens"]["refresh_token"]

    resp = await client.post(
        "/v1/auth/change-password",
        json={"current_password": OLD_PASSWORD, "new_password": NEW_PASSWORD},
        headers=_auth(old_access),
    )
    assert resp.status_code == 200
    new_refresh = resp.json()["refresh_token"]

    # Every pre-change refresh token family is revoked...
    dead = await client.post("/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert dead.status_code == 401

    # ...but the freshly-minted refresh from the response still rotates fine.
    alive = await client.post("/v1/auth/refresh", json={"refresh_token": new_refresh})
    assert alive.status_code == 200


@pytest.mark.asyncio
async def test_change_password_wrong_current_password(client: AsyncClient) -> None:
    body = await _signup(client)
    access = body["tokens"]["access_token"]

    resp = await client.post(
        "/v1/auth/change-password",
        json={"current_password": "not-the-password", "new_password": NEW_PASSWORD},
        headers=_auth(access),
    )
    assert resp.status_code == 401
    assert resp.json()["detail"]["error"]["code"] == "invalid_credentials"

    # Nothing changed: the old password still logs in, the session still works.
    me = await client.get("/v1/auth/me", headers=_auth(access))
    assert me.status_code == 200
    ok = await client.post("/v1/auth/login", json={"email": EMAIL, "password": OLD_PASSWORD})
    assert ok.status_code == 200


@pytest.mark.asyncio
async def test_change_password_rejects_weak_new_password(client: AsyncClient) -> None:
    body = await _signup(client)
    access = body["tokens"]["access_token"]

    resp = await client.post(
        "/v1/auth/change-password",
        json={"current_password": OLD_PASSWORD, "new_password": "short"},
        headers=_auth(access),
    )
    assert resp.status_code == 422  # same min-8 rule as signup


@pytest.mark.asyncio
async def test_change_password_rejects_unknown_fields(client: AsyncClient) -> None:
    """extra='forbid' — a typo'd field name must 422, not silently no-op."""
    body = await _signup(client)
    access = body["tokens"]["access_token"]

    resp = await client.post(
        "/v1/auth/change-password",
        json={
            "current_password": OLD_PASSWORD,
            "new_password": NEW_PASSWORD,
            "new_passwrd_typo": "oops",
        },
        headers=_auth(access),
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_change_password_requires_auth(client: AsyncClient) -> None:
    resp = await client.post(
        "/v1/auth/change-password",
        json={"current_password": OLD_PASSWORD, "new_password": NEW_PASSWORD},
    )
    assert resp.status_code == 401
