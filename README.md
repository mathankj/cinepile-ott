# Anjaneya OTT

Production-grade Netflix-like SVOD streaming platform.

> This is the **production build**. The pitch POC lives separately at `../netflix-poc/` and is now frozen.

## Status

**Phase 1 — Backend foundation (in progress, started 2026-06-02)**

We are building the backend end-to-end before touching the frontend. The frontend (React + Vite) starts after the backend's full V1 surface is implemented, tested, and load-validated.

## Repo layout

```
anjaneya-ott/
├── backend/             # FastAPI + SQLAlchemy + Alembic + pytest
├── frontend/            # React + Vite + TypeScript (built in Phase 2)
├── docs/
│   ├── architecture.md  # System overview, request lifecycle, why each piece exists
│   ├── api/             # REST API reference per version
│   ├── db-schema.md     # Entity diagram + column-by-column rationale
│   ├── decisions/       # ADRs — every meaningful technical decision and why
│   └── runbooks/        # Ops procedures (deploy, rollback, incident response)
├── infra/               # Deploy config, systemd units, nginx, env templates
├── scripts/             # Dev helpers (seed data, db reset, smoke tests)
└── README.md            # ← you are here
```

## Stack

| Layer | Choice | Why |
|---|---|---|
| Backend language | Python 3.13 | Pinned by stakeholder. Mature async story via FastAPI. |
| Backend framework | FastAPI | Async-first, OpenAPI generated free, fast, modern Python idioms. |
| ORM | SQLAlchemy 2.0 (async) | Industry standard; clean abstractions over Postgres + SQLite for tests. |
| Migrations | Alembic | The SQLAlchemy-native migration tool. Reversible, auditable. |
| Primary DB | PostgreSQL (Neon for dev) | ACID for users/billing/subscriptions. Neon = no local install needed. |
| Secondary DB | MongoDB (deferred) | Only added if a use case genuinely needs document flexibility (watch-event firehose, recommendation cache). |
| Cache / broker | Redis (deferred) | For sessions, rate limits, Celery queue. |
| Background jobs | Celery (deferred) | Triggers transcoding, sends emails. |
| Auth | JWT + bcrypt | No third-party lock-in. fastapi-users if it saves time. |
| Tests | pytest + httpx | Async test client. Real DB (SQLite for unit, Postgres for integration). |
| API docs | OpenAPI/Swagger at `/docs` | Auto-generated. Always in sync. |
| Frontend (later) | React 18 + Vite + TypeScript | Pinned by stakeholder. Plain SPA, not Next.js. |

Full reasoning in `docs/decisions/0001-stack.md`.

## Local development

See `docs/runbooks/dev-setup.md` (coming with the backend scaffold commit).

## Documentation philosophy

Every meaningful decision gets a one-page ADR in `docs/decisions/`. Every endpoint is in OpenAPI. Every runbook is in `docs/runbooks/`. If we change our mind, we **supersede** the old ADR rather than rewriting it — future maintainers see the reasoning trail.
