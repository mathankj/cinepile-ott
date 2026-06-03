# Changelog

All notable backend changes. Newest first. Each item references the commit hash.

## 2026-06-03 — Product flows: resume, history, free content
- `is_free` flag on `Title` and `Episode` for free-vs-paid gating; surfaces in `TitleSummary` and `TitleDetail` (`__commit__`)
- `GET /v1/me/history` paginated full viewing history (includes finished + hidden); `DELETE /v1/me/history/{title_id}` hard-deletes
- `/play` response includes `resume_at_sec` and `total_sec` so frontend skips a round trip
- `DELETE /v1/me/continue-watching/{title_id}` now soft-hides (preserves resume), not hard-deletes
- Migration `c599e9fb1787` for is_free columns
- 11 new edge tests

## 2026-06-03 — Backend QA pass (18 critical fixes)
- C1: expired subs no longer grant playback
- C2: concurrent subscribe idempotent (no double-charge)
- C3: search LIKE wildcards escaped
- C4: episode play checks parent series status
- C5: upload size limit actually enforced (`_SizeLimitedStream`)
- C6: upload content-type + extension whitelist
- C7: `GET /v1/titles/{id}/trailer` public endpoint
- C8: `GET /v1/titles/coming-soon`
- C9: sort field validated via regex
- C10: boto3 calls wrapped in `run_in_threadpool` (no event-loop blocking)
- C11: webhook idempotency via `webhook_events(event_id PK)`
- C12: webhook replay window (10 min) — old events rejected as stale
- C13: playback URL TTL 4h → 15min
- C14: continue-watching filters `completed`
- C15: "remove from continue" soft-hides (resume preserved)
- C16: asyncpg `statement_cache_size=0` for Neon pooler compat; statement_timeout=10s
- C17: `extra="forbid"` on update schemas (mass-assignment defense)
- C18: `/healthz` split into `/healthz` (liveness) + `/readyz` (readiness)
- Migrations: `67d9bd376b6d` (webhook_events), `117d9ec02783` (hidden_from_continue)
- 46 new edge tests
- Full QA report: `docs/runbooks/backend-qa-report.md`

## 2026-06-03 — Razorpay Orders API pivot (no KYC needed)
- New `BILLING_MODE=orders|subscriptions` setting (default `orders`)
- `POST /v1/payments/verify` — frontend Razorpay Checkout JS posts signed result; we verify HMAC + flip sub to active without waiting for the webhook
- Webhook handler supports both event families (`payment.*` for orders, `subscription.*` for subscriptions)
- Dev-only `GET /test-checkout` HTML helper page (Razorpay Checkout JS)
- Live e2e verified: subscribe → real netbanking payment → /payments/verify → sub active → /play returns B2 presigned URL

## 2026-06-03 — B2 storage layer end-to-end
- `STORAGE_*` env vars (provider-agnostic — B2, R2, S3, Storj all work)
- `app/services/storage.py` with `upload_fileobj`/`resolve_url` — public-bucket and private-bucket modes
- `POST /v1/admin/titles/{id}/upload-video` + `POST /v1/admin/episodes/{id}/upload-video`
- `playback.resolve_url()` returns presigned URLs for private buckets, full URLs for pre-seeded test streams
- Live smoke-tested against real Backblaze B2

## 2026-06-02 — Razorpay test integration
- Razorpay SDK + async wrapper (`run_in_threadpool`)
- Mock vs Razorpay provider switch via `BILLING_PROVIDER=auto|mock|razorpay`
- HMAC-SHA256 webhook signature verification with constant-time compare
- Plan + Subscription objects auto-created on first subscribe
- Test mode keys wired; live mode swap is one env-var change

## 2026-06-02 — Neon Postgres dev DB
- Switched dev DB from SQLite to Neon (us-east-1 free tier)
- asyncpg-compatible URL format documented
- `/healthz` proves DB reachability

## 2026-06-02 — Phase 1.5: rich catalog (movies + series)
- 20 tables, full data model: Title (movie|series), Season, Episode, Genre, Person + Credits, AudioTrack, SubtitleTrack, AvailabilityWindow, MaturityRating, Reaction, WatchlistItem, WatchProgress, AuditLog
- 28 routes: browse + filter + search, seasons + episodes, playback (movie + episode), reactions, watchlist, continue-watching, /v1/home rows
- Admin: lifecycle (draft→scheduled→published→archived→removed), publish/schedule/archive, role gating (admin + content_manager), audit log
- Alembic bootstrapped
- 44 → 65 tests

## 2026-06-02 — Phase 1: backend foundation
- FastAPI scaffold
- JWT auth with refresh rotation + reuse detection
- bcrypt password hashing (SHA-256 prehash for >72-byte safety)
- /v1/auth, /v1/films (later renamed /v1/titles), /v1/plans, /v1/subscriptions, /v1/history, /v1/admin
- pytest + httpx + structlog + alembic stack
- 44 initial integration tests
