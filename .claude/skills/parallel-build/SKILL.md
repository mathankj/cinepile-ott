---
name: parallel-build
description: Use when a task contains 2+ independent pieces of work (multiple independent endpoints, multiple model files, multiple test groups, multiple service scaffolds) that have no shared mutable state. Fans the work out to subagents with isolated worktrees so they cannot stomp each other's edits, then merges results back into the main branch.
---

# parallel-build — fanning work to multiple agents safely

Anjaneya OTT is large enough that one agent doing everything sequentially is the slow path. When a chunk of work decomposes into pieces that don't touch each other's files, fan it out.

## Trigger

Invoke this skill the moment any of these are true:

- Multiple endpoints, models, or schemas to create that live in **different files**
- A scaffold step that creates many small files (e.g., one test file per route group)
- A migration + the matching SQLAlchemy models + the matching Pydantic schemas (3 separate, mostly-independent artifacts)
- Anything labelled "do X for each of [A, B, C]"

**Do NOT** parallelize when:

- The work edits the same file (lock contention guaranteed)
- A later step depends on the output of an earlier step (sequential)
- The whole task fits in one short, focused agent turn (overhead > benefit)
- There are < 2 truly independent pieces

## How to fan out

1. **Decompose** the task into N independent units. Write each unit's contract on paper:
   - Exact files it owns (no overlap with siblings)
   - Inputs it can assume already exist (modules, models, fixtures)
   - Output it must produce (file paths + tests passing)
   - Forbidden: editing files outside its owned set
2. **Spawn N agents in a single message**, each with `subagent_type: general-purpose` and `isolation: worktree`. The single message is non-negotiable — that's what makes them parallel.
3. Each agent prompt must be self-contained (the subagent has no conversation history) and include:
   - Project root path (`C:\Users\matha\temp\anjaneya-ott\`)
   - The architecture doc reference (`docs/architecture.md`)
   - The ADR reference (`docs/decisions/0001-stack.md`)
   - The unit's owned files
   - The unit's contract
   - The test command it must run before reporting done
4. **Wait** for all to return.
5. **Verify** each agent's claimed work by reading the diffs (do not trust the summary alone — see global rule about "trust but verify").
6. **Merge** worktree branches back to main, resolving any unexpected conflicts.
7. **Run the full test suite** to catch boundary-violation bugs that per-unit tests missed.

## Example: scaffolding the four resource modules in one shot

The catalog, subscriptions, watch history, and admin route groups are mostly independent. Good fan-out candidate.

```
Agent A (worktree) — owns app/api/v1/films.py, app/services/catalog.py, app/schemas/film.py, tests/integration/test_films.py
Agent B (worktree) — owns app/api/v1/subscriptions.py, app/services/billing.py, app/schemas/subscription.py, tests/integration/test_subscriptions.py
Agent C (worktree) — owns app/api/v1/history.py, app/services/history.py, app/schemas/history.py, tests/integration/test_history.py
Agent D (worktree) — owns app/api/v1/admin.py, app/services/admin.py, tests/integration/test_admin.py
```

All four share read access to: `app/models/*.py`, `app/db/session.py`, `app/core/*`, `app/api/deps.py`. None of them edit these.

## Example prompt template for one subagent

```
You are scaffolding the films API for Anjaneya OTT.

Project root: C:\Users\matha\temp\anjaneya-ott\
Read first: README.md, docs/architecture.md, docs/api/v1.md (Catalog section), docs/db-schema.md (films table).

You own these files (create them):
- backend/app/schemas/film.py     (Pydantic request/response models)
- backend/app/services/catalog.py (pure business logic, no FastAPI imports)
- backend/app/api/v1/films.py     (FastAPI router; uses services + deps)
- backend/tests/integration/test_films.py (covers GET /v1/films, /v1/films/{id}, /v1/films/search)

You may READ but NEVER edit:
- backend/app/models/film.py
- backend/app/db/session.py
- backend/app/api/deps.py
- backend/app/core/*

Contract:
- All endpoints match docs/api/v1.md Catalog section exactly.
- Use AsyncSession via the db_session dep.
- Search uses Postgres tsvector via the search_vector column.
- Pagination is opaque cursor or page/page_size; pick one and document in your code.
- Error envelope matches docs/api/v1.md "Error envelope".

Before reporting done, run:
  cd backend && pytest tests/integration/test_films.py -v
All tests must pass. Report the test output verbatim.
```

## Merging back

```bash
# From main repo root
git checkout main
git merge --no-ff <worktree-branch-A>
git merge --no-ff <worktree-branch-B>
...
cd backend && pytest          # run the full suite
```

## When parallelization goes wrong

- **Two agents touched the same file** → my decomposition was wrong. Re-split.
- **One agent shipped failing tests** → don't merge. Send it back with the test output and a sharper contract.
- **Cross-file invariant broken** (e.g., schema mismatch with model) → the merge broke an invariant only visible in the full test suite. That's the cost we accept for speed; fix in main with a follow-up commit.

## Reporting

After every fan-out, append a one-line entry to `docs/runbooks/parallel-build-log.md`:

```
2026-06-02 — Catalog/Subs/History/Admin scaffold — 4 agents parallel — 6m wallclock vs ~25m sequential — 0 conflicts.
```

Build the dataset; tune decomposition over time.
