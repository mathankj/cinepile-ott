"""Auth endpoint integration tests."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

EMAIL = "alice@example.com"
PASSWORD = "supersecret123"


async def _signup(client: AsyncClient, email: str = EMAIL, password: str = PASSWORD) -> dict:
    resp = await client.post(
        "/v1/auth/signup",
        json={"email": email, "password": password, "full_name": "Alice"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.mark.asyncio
async def test_signup_returns_token_pair_and_user(client: AsyncClient) -> None:
    body = await _signup(client)
    assert body["tokens"]["access_token"]
    assert body["tokens"]["refresh_token"]
    assert body["tokens"]["token_type"] == "bearer"
    assert body["user"]["email"] == EMAIL
    assert body["user"]["role"] == "user"
    assert "password" not in body["user"]
    assert "password_hash" not in body["user"]


@pytest.mark.asyncio
async def test_signup_rejects_duplicate_email(client: AsyncClient) -> None:
    await _signup(client)
    resp = await client.post(
        "/v1/auth/signup",
        json={"email": EMAIL, "password": PASSWORD, "full_name": "Other"},
    )
    assert resp.status_code == 409
    assert resp.json()["detail"]["error"]["code"] == "email_already_registered"


@pytest.mark.asyncio
async def test_signup_rejects_weak_password(client: AsyncClient) -> None:
    resp = await client.post(
        "/v1/auth/signup",
        json={"email": EMAIL, "password": "short", "full_name": "Alice"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_login_returns_tokens(client: AsyncClient) -> None:
    await _signup(client)
    resp = await client.post("/v1/auth/login", json={"email": EMAIL, "password": PASSWORD})
    assert resp.status_code == 200
    body = resp.json()
    assert body["tokens"]["access_token"]
    assert body["user"]["email"] == EMAIL


@pytest.mark.asyncio
async def test_login_rejects_wrong_password(client: AsyncClient) -> None:
    await _signup(client)
    resp = await client.post("/v1/auth/login", json={"email": EMAIL, "password": "wrong-pass-9"})
    assert resp.status_code == 401
    assert resp.json()["detail"]["error"]["code"] == "invalid_credentials"


@pytest.mark.asyncio
async def test_login_rejects_unknown_email(client: AsyncClient) -> None:
    resp = await client.post(
        "/v1/auth/login", json={"email": "nobody@example.com", "password": "whatever9"}
    )
    assert resp.status_code == 401
    # Same error code as wrong-password → no email enumeration
    assert resp.json()["detail"]["error"]["code"] == "invalid_credentials"


@pytest.mark.asyncio
async def test_me_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/v1/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_returns_current_user(client: AsyncClient) -> None:
    body = await _signup(client)
    access = body["tokens"]["access_token"]
    resp = await client.get("/v1/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == EMAIL


@pytest.mark.asyncio
async def test_me_rejects_bad_token(client: AsyncClient) -> None:
    resp = await client.get("/v1/auth/me", headers={"Authorization": "Bearer not.a.token"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_rotates_token(client: AsyncClient) -> None:
    body = await _signup(client)
    refresh1 = body["tokens"]["refresh_token"]

    resp = await client.post("/v1/auth/refresh", json={"refresh_token": refresh1})
    assert resp.status_code == 200
    pair2 = resp.json()
    assert pair2["access_token"]
    assert pair2["refresh_token"]
    # New refresh must differ
    assert pair2["refresh_token"] != refresh1


@pytest.mark.asyncio
async def test_refresh_detects_reuse_and_revokes_family(client: AsyncClient) -> None:
    body = await _signup(client)
    refresh1 = body["tokens"]["refresh_token"]

    # First rotation succeeds
    r1 = await client.post("/v1/auth/refresh", json={"refresh_token": refresh1})
    assert r1.status_code == 200

    # Reusing the OLD refresh must fail AND wipe the new one too
    r_reuse = await client.post("/v1/auth/refresh", json={"refresh_token": refresh1})
    assert r_reuse.status_code == 401

    # The new refresh issued in r1 should now also be dead
    refresh2 = r1.json()["refresh_token"]
    r_after = await client.post("/v1/auth/refresh", json={"refresh_token": refresh2})
    assert r_after.status_code == 401


@pytest.mark.asyncio
async def test_logout_revokes_family(client: AsyncClient) -> None:
    body = await _signup(client)
    refresh = body["tokens"]["refresh_token"]

    resp = await client.post("/v1/auth/logout", json={"refresh_token": refresh})
    assert resp.status_code == 204

    # Refresh after logout must fail
    r = await client.post("/v1/auth/refresh", json={"refresh_token": refresh})
    assert r.status_code == 401
