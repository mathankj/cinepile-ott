"""
Security hardening tests (wave1/security):

- baseline security headers + HSTS-in-prod-only
- gzip compression
- /test-checkout gated out of prod
- login/signup rate limiting (sliding window per client IP)
- bcrypt null-byte fix: new hex scheme, legacy fallback, rehash-on-login
- DRM token secret fail-closed
- checkout_url carries a single-purpose checkout token (not the access token)
"""
from __future__ import annotations

import hashlib
import hmac
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import bcrypt as _bcrypt
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.security import (
    create_checkout_token,
    decode_checkout_token,
    hash_password,
    verify_password,
    verify_password_detailed,
)


# ---- Fixtures ----------------------------------------------------------------


@pytest_asyncio.fixture
async def prod_client(monkeypatch):
    """A client against a SEPARATE app instance built with app_env='prod'.

    The module-level app used by the normal `client` fixture was created with
    dev settings, so prod-only behaviour (HSTS, no /docs, no /test-checkout)
    needs its own app.
    """
    from app.core.config import get_settings
    from app.main import create_app

    monkeypatch.setenv("APP_ENV", "prod")
    get_settings.cache_clear()
    prod_app = create_app()
    transport = ASGITransport(app=prod_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    get_settings.cache_clear()


@pytest.fixture
def rate_limiting_enabled(monkeypatch):
    """Turn the limiter on (conftest disables it globally) with clean counters."""
    from app.core import ratelimit
    from app.core.config import get_settings

    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    get_settings.cache_clear()
    ratelimit.limiter.reset()
    yield
    get_settings.cache_clear()
    ratelimit.limiter.reset()


@pytest.fixture
def razorpay_orders_env(monkeypatch):
    monkeypatch.setenv("BILLING_PROVIDER", "razorpay")
    monkeypatch.setenv("BILLING_MODE", "orders")
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_test_FAKE")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "FAKE_SECRET")
    monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", "wh_test_secret")
    from app.core.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


# ---- 1. Security headers -------------------------------------------------------


@pytest.mark.asyncio
async def test_security_headers_present_in_dev(client) -> None:
    resp = await client.get("/healthz")
    assert resp.headers["x-content-type-options"] == "nosniff"
    assert resp.headers["x-frame-options"] == "DENY"
    assert resp.headers["referrer-policy"] == "no-referrer"
    # HSTS is prod-only — it would break plain-http local dev.
    assert "strict-transport-security" not in resp.headers


@pytest.mark.asyncio
async def test_hsts_header_present_in_prod(prod_client) -> None:
    resp = await prod_client.get("/healthz")
    assert (
        resp.headers["strict-transport-security"]
        == "max-age=31536000; includeSubDomains"
    )


# ---- 2. Gzip compression --------------------------------------------------------


@pytest.mark.asyncio
async def test_large_responses_are_gzipped(client) -> None:
    resp = await client.get("/openapi.json", headers={"Accept-Encoding": "gzip"})
    assert resp.status_code == 200
    assert resp.headers.get("content-encoding") == "gzip"


@pytest.mark.asyncio
async def test_small_responses_are_not_gzipped(client) -> None:
    # /healthz body is well under the 500-byte minimum_size.
    resp = await client.get("/healthz", headers={"Accept-Encoding": "gzip"})
    assert resp.headers.get("content-encoding") != "gzip"


# ---- 3. Dev checkout page gated out of prod -------------------------------------


@pytest.mark.asyncio
async def test_test_checkout_not_registered_in_prod(prod_client) -> None:
    resp = await prod_client.get("/test-checkout", params={"token": "anything"})
    assert resp.status_code == 404


# ---- 4. Rate limiting ------------------------------------------------------------


@pytest.mark.asyncio
async def test_login_rate_limited_after_10_per_minute(rate_limiting_enabled, client) -> None:
    payload = {"email": "nobody@example.com", "password": "wrong-pass-123"}
    for _ in range(10):
        resp = await client.post("/v1/auth/login", json=payload)
        assert resp.status_code == 401  # wrong creds, but not yet limited

    resp = await client.post("/v1/auth/login", json=payload)
    assert resp.status_code == 429
    assert resp.json()["detail"]["error"]["code"] == "rate_limited"
    assert int(resp.headers["retry-after"]) >= 1


@pytest.mark.asyncio
async def test_signup_rate_limited_after_5_per_minute(rate_limiting_enabled, client) -> None:
    for i in range(5):
        resp = await client.post(
            "/v1/auth/signup",
            json={"email": f"rl{i}@example.com", "password": "password123"},
        )
        assert resp.status_code == 201

    resp = await client.post(
        "/v1/auth/signup",
        json={"email": "rl-overflow@example.com", "password": "password123"},
    )
    assert resp.status_code == 429
    assert resp.json()["detail"]["error"]["code"] == "rate_limited"


@pytest.mark.asyncio
async def test_rate_limit_keys_on_forwarded_for(rate_limiting_enabled, client) -> None:
    """Behind the proxy the first X-Forwarded-For entry is the real client —
    exhausting one IP's budget must not block a different IP."""
    payload = {"email": "nobody@example.com", "password": "wrong-pass-123"}
    for _ in range(10):
        await client.post(
            "/v1/auth/login", json=payload, headers={"X-Forwarded-For": "203.0.113.1"}
        )
    blocked = await client.post(
        "/v1/auth/login", json=payload, headers={"X-Forwarded-For": "203.0.113.1"}
    )
    assert blocked.status_code == 429

    other_ip = await client.post(
        "/v1/auth/login", json=payload, headers={"X-Forwarded-For": "203.0.113.2"}
    )
    assert other_ip.status_code == 401  # not rate limited


# ---- 5. bcrypt null-byte fix ------------------------------------------------------


def _legacy_hash(password: str) -> str:
    """Reproduce the OLD scheme: bcrypt over the raw sha256 digest (which can
    contain NUL bytes that bcrypt truncates at). Low rounds: tests only."""
    digest = hashlib.sha256(password.encode("utf-8")).digest()
    return _bcrypt.hashpw(digest, _bcrypt.gensalt(rounds=4)).decode("utf-8")


def test_new_hash_round_trip() -> None:
    h = hash_password("correct horse battery staple")
    valid, needs_rehash = verify_password_detailed("correct horse battery staple", h)
    assert valid
    assert not needs_rehash  # current scheme — nothing to upgrade
    assert not verify_password("wrong password", h)


def test_legacy_hash_still_verifies_and_signals_rehash() -> None:
    h = _legacy_hash("legacy-password-99")
    valid, needs_rehash = verify_password_detailed("legacy-password-99", h)
    assert valid
    assert needs_rehash
    assert not verify_password("not-the-password", h)


def test_nul_digest_password_handled_by_both_schemes() -> None:
    """'pw142' has a sha256 digest that BEGINS with a 0x00 byte — exactly the
    class of password that lost entropy under the legacy raw-digest scheme
    (bcrypt's C implementation truncates input at the first NUL). The new hex
    scheme feeds bcrypt NUL-free ascii, and legacy hashes of such passwords
    still verify via the fallback and get flagged for upgrade."""
    password = "pw142"
    assert hashlib.sha256(password.encode()).digest()[0] == 0

    # New scheme: clean round trip, wrong passwords rejected.
    fresh = hash_password(password)
    assert verify_password(password, fresh)
    assert not verify_password("pw280", fresh)  # also a leading-0x00 digest

    # Legacy hash of the same password: still valid, but flagged for rehash.
    legacy = _legacy_hash(password)
    valid, needs_rehash = verify_password_detailed(password, legacy)
    assert valid
    assert needs_rehash


@pytest.mark.asyncio
async def test_legacy_hash_upgraded_on_login(client, db_engine) -> None:
    from app.models.user import User

    password = "legacy-password-42"
    legacy = _legacy_hash(password)
    factory = async_sessionmaker(bind=db_engine, expire_on_commit=False)
    async with factory() as s:
        user = User(email="legacy@example.com", password_hash=legacy, role="user")
        s.add(user)
        await s.commit()
        user_id = user.id

    resp = await client.post(
        "/v1/auth/login", json={"email": "legacy@example.com", "password": password}
    )
    assert resp.status_code == 200, resp.text

    # The stored hash was transparently upgraded to the current scheme.
    async with factory() as s:
        refreshed = await s.get(User, user_id)
        assert refreshed.password_hash != legacy
        valid, needs_rehash = verify_password_detailed(password, refreshed.password_hash)
        assert valid
        assert not needs_rehash


# ---- 6. DRM fail-closed ------------------------------------------------------------


def test_settings_reject_drm_without_token_secret() -> None:
    from pydantic import ValidationError

    from app.core.config import Settings

    common = {
        "database_url": "sqlite+aiosqlite:///:memory:",
        "jwt_secret": "test-secret-test-secret-test-secret-32",
        "_env_file": None,
    }
    with pytest.raises(ValidationError, match="DRM_TOKEN_SECRET"):
        Settings(drm_widevine_license_url="https://lic.example/wv", **common)
    with pytest.raises(ValidationError, match="DRM_TOKEN_SECRET"):
        Settings(drm_provider="ezdrm", **common)

    # With the secret present, the same config is valid.
    ok = Settings(
        drm_widevine_license_url="https://lic.example/wv",
        drm_provider="ezdrm",
        drm_token_secret="provider-shared-secret",
        **common,
    )
    assert ok.drm_token_secret == "provider-shared-secret"


def test_playback_drm_block_fails_closed_without_secret(monkeypatch) -> None:
    """Even if settings were mutated after startup, the playback service must
    refuse to sign DRM license tokens with jwt_secret."""
    from app.core.config import get_settings
    from app.services import playback

    settings = get_settings()
    monkeypatch.setattr(settings, "drm_widevine_license_url", "https://lic.example/wv")
    monkeypatch.setattr(settings, "drm_token_secret", None)

    with pytest.raises(RuntimeError, match="DRM_TOKEN_SECRET"):
        playback._build_drm_config(1, "title", 1)


# ---- 7. Checkout token (token-in-URL fix, backend half) ----------------------------


@pytest.mark.asyncio
async def test_checkout_url_embeds_scoped_checkout_token(
    razorpay_orders_env, auth_client, make_plan
) -> None:
    client, access_token, user = auth_client
    await make_plan(code="monthly")

    with patch(
        "app.services.razorpay_client.create_order",
        return_value={"id": "order_TOK1", "amount": 19900, "currency": "INR"},
    ):
        resp = await client.post("/v1/subscriptions", json={"plan_code": "monthly"})
    assert resp.status_code == 201

    checkout_url = resp.json()["checkout_url"]
    token = parse_qs(urlparse(checkout_url).query)["token"][0]
    assert token != access_token  # NOT the user's access token

    claims = decode_checkout_token(token)
    assert claims["purpose"] == "checkout"
    assert claims["order_id"] == "order_TOK1"
    assert claims["sub"] == str(user.id)

    # The URL is complete — it opens as-is.
    page = await client.get(checkout_url)
    assert page.status_code == 200
    assert "Razorpay" in page.text


@pytest.mark.asyncio
async def test_test_checkout_rejects_access_tokens(auth_client) -> None:
    client, access_token, _ = auth_client
    resp = await client.get("/test-checkout", params={"token": access_token})
    assert resp.status_code == 403
    assert resp.json()["detail"]["error"]["code"] == "invalid_checkout_token"


@pytest.mark.asyncio
async def test_test_checkout_requires_token(client) -> None:
    resp = await client.get("/test-checkout")
    assert resp.status_code == 422  # token query param is mandatory


@pytest.mark.asyncio
async def test_payments_verify_accepts_matching_checkout_token(
    razorpay_orders_env, auth_client, make_plan
) -> None:
    """The dev test-checkout page authenticates the verify call with the
    checkout token from its URL — no access token involved."""
    client, _, _ = auth_client
    await make_plan(code="monthly", price_cents=19900)

    with patch(
        "app.services.razorpay_client.create_order",
        return_value={"id": "order_TOK2", "amount": 19900, "currency": "INR"},
    ):
        resp = await client.post("/v1/subscriptions", json={"plan_code": "monthly"})
    checkout_token = parse_qs(urlparse(resp.json()["checkout_url"]).query)["token"][0]

    sig = hmac.new(b"FAKE_SECRET", b"order_TOK2|pay_TOK2", hashlib.sha256).hexdigest()
    with patch(
        "app.services.razorpay_client.fetch_payment",
        return_value={"id": "pay_TOK2", "status": "captured", "amount": 19900},
    ):
        verify = await client.post(
            "/v1/payments/verify",
            json={
                "razorpay_order_id": "order_TOK2",
                "razorpay_payment_id": "pay_TOK2",
                "razorpay_signature": sig,
            },
            # Request-level header overrides the fixture's access token.
            headers={"Authorization": f"Bearer {checkout_token}"},
        )
    assert verify.status_code == 200, verify.text
    assert verify.json()["status"] == "active"


@pytest.mark.asyncio
async def test_payments_verify_rejects_checkout_token_for_other_order(
    razorpay_orders_env, auth_client, make_plan
) -> None:
    """A checkout token is scoped: it cannot verify a different order."""
    client, _, user = auth_client
    await make_plan(code="monthly")

    with patch(
        "app.services.razorpay_client.create_order",
        return_value={"id": "order_TOK3", "amount": 19900, "currency": "INR"},
    ):
        resp = await client.post("/v1/subscriptions", json={"plan_code": "monthly"})
    sub_id = resp.json()["id"]

    # Token minted for a DIFFERENT order than the one being verified.
    wrong_scope_token = create_checkout_token(
        user_id=user.id, subscription_id=sub_id, order_id="order_SOMETHING_ELSE"
    )
    sig = hmac.new(b"FAKE_SECRET", b"order_TOK3|pay_TOK3", hashlib.sha256).hexdigest()
    verify = await client.post(
        "/v1/payments/verify",
        json={
            "razorpay_order_id": "order_TOK3",
            "razorpay_payment_id": "pay_TOK3",
            "razorpay_signature": sig,
        },
        headers={"Authorization": f"Bearer {wrong_scope_token}"},
    )
    assert verify.status_code == 401
