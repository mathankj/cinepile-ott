# ADR-0001 — Stack choice for Anjaneya OTT production build

**Status:** Accepted
**Date:** 2026-06-02
**Decider:** Mathan (tech lead), with stakeholder input

## Context

After the POC was approved, we need a production build. The stakeholder gave specific stack constraints:

- **Backend in Python** (rejected: Node.js as a backend choice)
- **Frontend in React, not Next.js** (rejected: keeping Next.js from the POC)
- **PostgreSQL primary; MongoDB only if needed**
- **Backend complete before frontend starts**

These are constraints, not opinions to debate. The decision is about *which Python framework, which ORM, which auth strategy, how to handle Postgres without local Docker*.

## Decision

| Concern | Choice | Rejected alternatives |
|---|---|---|
| Web framework | **FastAPI** | Django REST (heavier, sync-first), Flask (no async, no built-in OpenAPI), Starlette raw (too low-level), Litestar (smaller community) |
| ORM | **SQLAlchemy 2.0 (async)** | Tortoise ORM (smaller ecosystem), Pony (academic), raw asyncpg (no migrations story) |
| Migrations | **Alembic** | yoyo-migrations, raw SQL files |
| Database hosting (dev) | **Neon serverless Postgres** | Supabase (heavier feature set, paying for things we don't use), local Postgres install (Windows install friction, no Docker on this machine) |
| Auth | **Custom JWT + bcrypt** (with optional fastapi-users later if it saves time) | Auth0/Clerk (vendor lock + cost), session cookies (don't compose with React SPA + future mobile cleanly) |
| Background jobs (Phase 2) | **Celery + Redis** | RQ (less mature retry/scheduling), arq (good but smaller), Dramatiq |
| Tests | **pytest + httpx async client** | unittest (verbose), pytest-django (we're not Django) |
| Frontend (Phase 2) | **React 18 + Vite + TypeScript** | Plain Webpack CRA (deprecated/slow), Next.js (vetoed by stakeholder) |

## Why FastAPI specifically

- **Async-native.** Most of our work is I/O — DB calls, billing webhooks, signed-URL generation. Async lets a single worker handle many concurrent connections cheaply.
- **OpenAPI generated free.** Every endpoint we write produces a Swagger doc at `/docs` automatically. The frontend team gets a contract without us writing one.
- **Pydantic v2 validation.** Request/response schemas validate themselves at the framework boundary — no manual `if not request.body.get('email'):` plumbing.
- **Modern Python idioms.** Type hints everywhere. Editor autocomplete actually works. New hires onboard faster.
- **Production proof:** Used by Microsoft, Uber, Netflix (internal tools), Cloudflare, Anthropic, OpenAI.

## Why SQLAlchemy 2.0 over Tortoise or raw asyncpg

- SQLAlchemy is the industry standard — every senior Python engineer has used it. Hiring is easier.
- 2.0 finally has a clean async story that works.
- Lets us swap SQLite (tests) ↔ Postgres (everywhere else) with one URL change.
- Alembic is built for it; migrations are reversible and reviewable in PRs.

## Why Neon for dev Postgres

- The dev machine has **no Docker and no local Postgres**. Installing Postgres on Windows is a 20-minute distraction every new contributor pays.
- Neon's free tier gives us a real Postgres URL in under 60 seconds.
- Branches per developer or per PR are one CLI call (Neon-specific superpower).
- Switch to self-hosted Postgres for production via env var; no code change.

## Why JWT over sessions

- Stateless — horizontal scaling FastAPI workers requires no sticky sessions or shared session store.
- Cleaner story when mobile apps land in Phase 3.
- Refresh-token rotation gives us "log out everywhere" by versioning the token claim against a per-user counter in DB.

## Consequences

**Good:**
- One language across backend, scripts, ML/recommendations (Phase 2).
- Auto-generated OpenAPI means frontend team can mock against `/openapi.json`.
- No SaaS lock-in for auth.

**Costs we accept:**
- Python is slower than Go/Rust at raw CPU. We are I/O-bound, so this rarely bites. If it ever does (rare hot path), we drop to Cython/Rust for that one function.
- SQLAlchemy 2.0 async is newer than its sync mode — sharper edges (we'll document them as we hit them in `docs/runbooks/`).
- Custom auth means we own bugs in our auth code. Mitigated by: bcrypt + standard JOSE library, tests covering token tampering / expiry / refresh rotation, no homegrown crypto.

## What would make us revisit this

- If a single Python worker can't handle our load at hardware reasonable cost → consider Go for the playback-URL hot path only.
- If the frontend team independently wants SSR for SEO → revisit Next.js choice (Phase 2).
- If we add real-time features (chat, watch parties) → may need an additional service (Node/Go/Phoenix) alongside the REST API.
