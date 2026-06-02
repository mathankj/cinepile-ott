# Project rules for Claude — Anjaneya OTT

## Read first
1. `README.md` — project overview
2. `docs/architecture.md` — what we're building and why each piece exists
3. `docs/decisions/0001-stack.md` — locked stack choices
4. `docs/api/v1.md` — endpoint contracts (live OpenAPI is the source of truth)
5. `docs/db-schema.md` — tables and indexes

## Hard rules

- **Backend-first.** Do not write a single line of frontend code in this repo until the full backend V1 surface in `docs/api/v1.md` is implemented, tested, and the load smoke test in `docs/runbooks/load-test-baseline.md` is recorded.
- **No copy from `../netflix-poc/`.** That project is frozen as the pitch artifact. This is a fresh codebase.
- **No Next.js.** Frontend is React + Vite when Phase 2 starts. ADR-0001 is settled — do not re-litigate.
- **Mongo only when needed.** Postgres is the default. If you reach for Mongo, write an ADR explaining the use case first.
- **Every meaningful technical decision gets an ADR** in `docs/decisions/`. One page, numbered.
- **Every endpoint gets a test** before it's considered done. No exceptions.
- **Never edit applied Alembic migrations.** Add a new one.

## Code style

- Type hints everywhere. `mypy --strict` is the goal (we'll add it once code exists to lint).
- Routes are thin. Business logic lives in `app/services/`. Routes are HTTP glue only.
- `app/models/` (SQLAlchemy) ↔ DB only. `app/schemas/` (Pydantic) ↔ HTTP only. Never leak ORM models out of services.
- Comments only when the *why* is non-obvious. Don't restate what the code says.

## Stakeholder reads the code
The client / stakeholder may read source. Keep names clear, comments useful, and avoid clever one-liners that need explaining.

## When fanning out work
Use the `parallel-build` skill at `.claude/skills/parallel-build/SKILL.md`. Do not invent your own decomposition strategy.

## When you're not sure
Read the relevant doc in `docs/`. If the answer isn't there and it's a real decision, write an ADR before coding. If it's a small judgement call, just make it and note it in a comment.
