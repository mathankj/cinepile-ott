# Changelog

All notable backend changes. Newest first. Each item references the commit hash.

## 2026-06-10 — Completion push (wave 1 + wave 2 merges)

### Security hardening
- Security headers on every response: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, HSTS (prod only)
- Gzip compression on JSON responses >500 bytes
- Rate limiting on unauthenticated auth endpoints: login 10/min, signup 5/min per client IP (in-process sliding window; Redis swap documented for multi-worker)
- bcrypt prehash fix: SHA-256 **hexdigest** (NUL-free) replaces raw digest — raw digests contain 0x00 ~12% of the time and bcrypt truncates at the first NUL. Legacy hashes still verify and are transparently rehashed on next successful login
- `POST /v1/auth/change-password` — revokes all other sessions (refresh families + session_version bump), returns a fresh TokenPair for the current session
- Razorpay `POST /v1/payments/verify` now fetches the payment from Razorpay's API and requires `status == "captured"` AND amount == plan price — a valid signature alone no longer activates a subscription
- Webhook strictness: `created_at` and `X-Razorpay-Event-Id` are now required (400 if missing) so the replay window and idempotency checks can't be silently bypassed
- DRM license-token signing fails closed: refuses to sign with `JWT_SECRET` if `DRM_TOKEN_SECRET` is unset while DRM is configured
- Dev `/test-checkout` URL no longer carries the user's real access token — replaced with a single-purpose checkout token (10-min TTL, `purpose='checkout'`, scoped to one order, rejected everywhere else)
- Dev checkout page is not registered at all when `APP_ENV=prod`
- Cache-invalidation fixes on all admin writes — every catalog mutation (create/update/publish/schedule/archive/delete/restore, seasons, episodes, genres, uploads) busts the titles/detail/season/similar/home/genres caches (`fb97faf` + waves)

### Performance
- `noload("*")` on all list/row queries that project into `TitleSummary` — kills the lazy `selectin` fan-out (anonymous `/v1/home` build: 16 SELECTs → 2)
- Per-key home-cache build locks — cache stampede protection without serializing unrelated users behind one global lock
- All in-process TTL caches bounded (512 entries, FIFO eviction) so crawler-shaped traffic can't grow them forever
- Scheduled-title promotion throttled to once per 30 s per process (reset on admin writes so fresh schedules go live on the next read)
- Migration `4b8e21c0a9d7`: hot-path DB indexes on titles + watch_progress
- Frontend vendor chunk split (react / router / hls / motion / i18n / misc): entry chunk 522 KB → 33 KB; hls.js only downloads when the player opens
- Watch-chunk hover prefetch (Billboard + TitleCard preload `pages/Watch` on hover/focus)
- hls.js tuning: `startFragPrefetch: true` + buffer limits for faster start

### New endpoints
- `GET /v1/titles/{id}/similar` — "More Like This" (public, shared-genre, view_count desc, cached)
- `POST /v1/admin/titles/{id}/restore` — undo soft-delete (restores to `archived`)
- `GET /v1/admin/titles-deleted` — paginated soft-deleted titles list
- `GET /v1/admin/titles/{id}/seasons` — full series structure incl. drafts, for the editor
- `PATCH /v1/admin/genres/{id}` + `DELETE /v1/admin/genres/{id}` (delete is 409 `genre_in_use` while referenced)
- Last-admin guard: demoting the only remaining admin via `PATCH /v1/admin/users/{id}/role` → 409

### Frontend features
- In-app trailer playback (`/watch/trailer/:id` — no more external links)
- "More Like This" row on title detail
- Next-episode auto-advance with 10 s countdown overlay
- Skip-Recap overlay (episode `recap_start_sec`/`recap_end_sec` markers)
- Admin Seasons/Episodes editor — create/edit episodes, skip markers, publish/delete, per-episode video + subtitle uploads with progress bars
- Admin Genres page (full CRUD) and TitleEditor genres/artwork (poster/backdrop/trailer URLs)/schedule fields
- Deleted-titles tab with one-click restore in the admin titles list
- Account page (`/account`) with change-password form (swaps tokens in place)
- TitleDetail loading skeleton shaped like the real page

### Profile scoping (real profiles)
- Migration `8c4f72d1e6a3`: `profile_id` on watchlist / watch_progress / reactions
- `X-Profile-Id` header (verified against the authenticated user; invalid/missing falls back to the legacy NULL-profile scope)
- Continue-watching, My List, reactions, history, and home rows are now per-profile
- Kid profiles: U-rated-only home rows and a hard server-side playback gate (403 `kid_profile_restricted`). Known gap: full catalog browse/search is not yet kid-filtered — but playback always is

### i18n
- Full sweep of user-facing strings incl. the player: 94 → 187 keys, ×3 locales (en/hi/ta)

Backend tests: 133 → 224.

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
