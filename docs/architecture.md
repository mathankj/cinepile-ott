# Anjaneya OTT — Architecture (Phase 1: Backend V1)

**Last updated:** 2026-06-02
**Status:** Living document. Update on every meaningful change.

---

## 1. Goal of Phase 1

Deliver a **complete, tested, documented backend API** that a frontend could integrate against to run an end-to-end SVOD product:

1. A user can sign up, log in, and stay logged in.
2. A user can subscribe to a plan (mock billing in V1; real provider in V1.1).
3. A user can browse films, search, and view a film detail page.
4. A user can request a playback URL and stream a film.
5. A user's watch progress is persisted and resumable.
6. An admin can upload film metadata.

Phase 1 deliberately **excludes**: real billing, real video transcoding, recommendations, profiles, multi-device sync, DRM, AI features. Each becomes its own later phase.

## 2. High-level shape

```
┌─────────────────────────┐
│  Future React frontend  │   (Phase 2 — not built yet)
└──────────┬──────────────┘
           │  HTTPS / JSON
           ▼
┌─────────────────────────┐
│   FastAPI app           │     ──► OpenAPI at /docs
│   (Python 3.13, async)  │     ──► /healthz at /healthz
└──────────┬──────────────┘
           │
           ├──► PostgreSQL (Neon)     ── users, films, subscriptions, watch_history
           ├──► Object storage stub   ── stores film file pointers (real S3 in V1.1)
           └──► Redis (Phase 2)       ── sessions, rate limit, Celery broker
```

## 3. Module layout (backend)

```
backend/
├── app/
│   ├── main.py              # FastAPI app instance + middleware + router include
│   ├── core/
│   │   ├── config.py        # pydantic-settings, loads .env, fails fast on missing keys
│   │   ├── security.py      # password hashing, JWT encode/decode, time-constant compare
│   │   └── logging.py       # structured logs (json in prod, pretty in dev)
│   ├── db/
│   │   ├── base.py          # SQLAlchemy declarative base, async engine factory
│   │   └── session.py       # AsyncSession dependency for routes
│   ├── models/              # SQLAlchemy ORM models — one file per aggregate
│   │   ├── user.py
│   │   ├── film.py
│   │   ├── subscription.py
│   │   └── watch_history.py
│   ├── schemas/             # Pydantic request/response schemas — never leak ORM models
│   │   ├── user.py
│   │   ├── film.py
│   │   └── ...
│   ├── services/            # Business logic — pure functions/classes, no FastAPI imports
│   │   ├── auth.py
│   │   ├── catalog.py
│   │   ├── billing.py       # mock provider in V1, real in V1.1
│   │   └── playback.py      # signed-URL generation
│   └── api/
│       ├── deps.py          # current_user, current_admin, db_session deps
│       └── v1/
│           ├── auth.py
│           ├── films.py
│           ├── subscriptions.py
│           ├── history.py
│           └── admin.py
├── alembic/                 # migrations
├── tests/
│   ├── conftest.py          # test db, test client, fixtures
│   ├── unit/                # service-layer tests (no HTTP)
│   ├── integration/         # full request → DB tests via TestClient
│   └── e2e/                 # end-to-end user journeys
├── pyproject.toml
├── alembic.ini
└── .env.example
```

**Boundary rule:** `models` ↔ DB only. `schemas` ↔ HTTP only. `services` ↔ pure logic. `api` ↔ HTTP glue. A route never touches a SQLAlchemy model directly; it calls a service which returns a schema or domain object.

## 4. Request lifecycle (example: GET /films/{id})

1. ASGI server (uvicorn) hands request to FastAPI.
2. Middleware: request-id injection, CORS, structured access log.
3. Route handler `app/api/v1/films.py::get_film` runs.
4. Dependency: `db` → an `AsyncSession` is opened per request.
5. Dependency: `current_user` (optional here) → validates `Authorization: Bearer ...`.
6. Handler calls `catalog_service.get_by_id(db, film_id)`.
7. Service fetches via SQLAlchemy, returns a domain `Film` (or 404s).
8. Handler maps to `FilmRead` pydantic schema and returns it.
9. Middleware finalizes log line with status + latency.

## 5. Versioning

All routes live under `/v1/...`. When we make breaking changes we publish `/v2/` alongside `/v1/` and deprecate `/v1/` on a published schedule (90 days). OpenAPI exposes both.

## 6. Configuration

All runtime config comes from environment variables, loaded into `Settings` (a pydantic `BaseSettings`). Required keys fail at startup (not on first use). See `.env.example` for the full list.

## 7. Observability (V1 baseline)

- Structured JSON logs to stdout (production) or pretty colored logs (dev).
- `/healthz` returns DB connectivity check + version.
- Every request gets a `X-Request-ID` (generated if missing).
- Request latency logged.
- Phase 2 adds: Prometheus metrics endpoint, Sentry integration, OpenTelemetry traces.

## 8. Security baseline (V1)

- Passwords hashed with bcrypt (passlib), never logged.
- JWT access tokens (short-lived 15min) + refresh tokens (7d, rotating).
- CORS allowlist driven by `ALLOWED_ORIGINS` env var.
- All write endpoints require auth; admin endpoints require admin role.
- Rate limiting deferred to Phase 2 (Redis-backed).
- Secrets never committed; `.env.example` documents required keys without values.

## 9. Scale story (what we built so the team can grow it)

V1 runs as a single FastAPI process behind nginx. Postgres on Neon (managed). This easily handles thousands of concurrent users for catalog/auth flows — those are the cheap paths.

**Where scale shows up first:**

- *Playback URL generation* — every "Play" button hits this. Cache the signed URL per (user, film) for its TTL in Redis (Phase 2).
- *Watch history writes* — high volume; batch into a queue and write async. Phase 2 adds Redis stream + worker.
- *Video bytes themselves* — NOT served by our API. CDN does that (BunnyCDN/Cloudflare). Phase 2.

**How we grow:** horizontal-scale FastAPI workers behind nginx (stateless service, JWT means no sticky sessions). Postgres scales vertically first, then read-replicas. Hot paths get Redis caching. Background work moves to Celery workers.

Load-test results land in `docs/runbooks/load-test-baseline.md` after the smoke test is run.

## 10. What's intentionally NOT here yet

| Capability | When |
|---|---|
| Real billing provider (Razorpay/Stripe) | V1.1 |
| Real video transcoding (FFmpeg workers, HLS packaging) | V2 |
| DRM (Widevine/FairPlay) | V3, only when premium content arrives |
| Recommendations | V2 |
| Profiles (multi-user within an account) | V2 |
| Mobile apps | V3 |
| Smart TV apps | V4 |

Each becomes its own ADR + spec when we get there.
