# Backend QA Audit — first-pass gap list

**Date:** 2026-06-03 (pre-research)
**Status:** Working doc — will be merged with research-agent findings before implementation.

The user asked for an end-to-end QA pass before frontend connects. This is what I see in the code that's missing or thin, *before* the research agents return their independent findings.

---

## A. Catalog / browse — gaps I already see

### A1. Scheduled-publish auto-promotion runs on EVERY read
`catalog.auto_promote_scheduled()` runs at the top of `list_titles()` and `get_title()`. Two issues:
- **Write on every read** — even when nothing needs promoting. We do an UPDATE...WHERE that no-ops 99.9% of the time but still costs a query. Should be: only run if there's at least one scheduled title close to publish_at.
- **Race condition** under concurrent reads: two requests both try to promote the same row simultaneously. SQL handles it fine but the audit-log entry won't fire (no audit on auto-promote). For prod this should be a background job that writes an audit entry once per promotion.

### A2. "Coming soon" is not surfaced
A scheduled title is **invisible** until `publish_at` passes. Real OTTs (Netflix, Hoichoi) show "coming soon" cards with the release date. Our backend has no endpoint for this. Fix: add `?include=upcoming` to `GET /v1/titles` that surfaces scheduled titles in a separate row.

### A3. Trailer endpoint doesn't exist
`TitleAsset.kind = 'trailer'` is defined and used by the data model, but **no endpoint returns trailers**. The frontend has nowhere to fetch trailer URLs. Need: `GET /v1/titles/{id}/trailer` returning a (possibly presigned) URL.

### A4. Trailers don't need entitlement
Right now `playback.issue_movie_ticket` requires an active subscription. Trailers should be **playable without auth** (they're marketing). Different code path.

### A5. Hover-preview clips
Netflix-style hover-play uses a separate 20-30s short clip per title, lower bitrate. Out of scope but worth a `TitleAsset.kind = 'preview'` documented for V2.

### A6. Search edge cases
- Empty query → currently returns `[]`. Good.
- Special chars: `'%'` and `'_'` in `LIKE` patterns are wildcards we don't escape. **Real bug**: `q=%` returns all titles.
- Very long query: no length cap. DoS vector.
- No "fuzzy" / typo tolerance. Acceptable for V1.5.

### A7. Filter combinations untested
We accept `type`, `genre`, `language`, `country`, `year_from`, `year_to`, `sort` — but I haven't tested all permutations. Need integration tests for the matrix.

### A8. Sort field not validated
`sort=foo` falls back silently to `-published_at`. Should be either an enum (Literal) or 400 on unknown sort.

### A9. Pagination boundaries
- `page=0` → we coerce to 1. OK.
- `page=999999` → returns empty list with the full total count. Wastes a Postgres query. Could short-circuit if `page * page_size > total`.
- `page_size=100` is the cap. Sensible.

## B. Episode / series — gaps

### B1. Weekly release flow not fully proven
The data model supports `episode.status` independent of `series.status` — but I haven't tested: publish series + S1E1 today, leave S1E2 as `draft` or `scheduled`. Does `/v1/titles/{id}/seasons/1` only return the published episode? Need test.

### B2. Episode-level auto-promote works but is silent
`auto_promote_scheduled()` flips episodes the same way. No audit entry. Same issue as A1.

### B3. "Next-episode" hint
When user finishes S1E1, the player needs to know S1E2 exists. There's no dedicated endpoint — frontend has to fetch the whole season. For V1.5 that's fine but a `/v1/episodes/{id}/next` would be nicer.

### B4. Episode play doesn't check parent series status
`issue_episode_ticket()` checks the episode is published, but not the parent series. If the series is `archived` or `removed`, the episode shouldn't play. **Real bug** — needs verification.

## C. Subscription lifecycle — gaps

### C1. **CRITICAL: expired subscriptions are not blocked**
`has_active_subscription()` returns True if status='active' regardless of `current_period_end`. A subscription whose period ended a month ago still grants play access. **This is the single biggest correctness bug in the system.**
Fix: also check `current_period_end > now()` in the query.

### C2. No grace period
Real OTTs give 24-72 hour grace on failed renewal. We have no concept. For V1.5 not blocking but worth documenting.

### C3. Concurrent subscribe race
Two browser tabs hitting `POST /v1/subscriptions` simultaneously could create two pending Razorpay orders. We check `existing = get_my_subscription(...)` which only matches `status='active'`. Pending rows aren't blocking. **Possible double-charge.**
Fix: `existing = ... where status in ('active', 'pending')`.

### C4. Cancellation doesn't actually expire
`cancel()` sets `cancel_at_period_end=True` but the local row stays `active` until `current_period_end`. No background job flips it to `cancelled` at period end. For V1.5 acceptable if C1 is fixed (period-end check covers both expiry and cancellation).

### C5. Plan switch / upgrade not supported
A user with monthly can't upgrade to annual mid-period. Not a blocker for V1.5.

## D. Auth — gaps

### D1. CORS configured but untested
We have `ALLOWED_ORIGINS` env var and `CORSMiddleware`. No tests cover that the wrong origin gets blocked. Easy add.

### D2. Mass-assignment via update endpoints
`UserUpdate` schema doesn't exist (we don't have `/v1/me/update`). But if a user could PATCH their own role we'd be in trouble. Not a current bug, but worth a regression test if/when we add user-self-update.

### D3. BOLA on watch-history
`GET /v1/me/continue-watching` filters by `user_id == current_user.id` — looks correct, but worth a regression test that user B can't see user A's history.

### D4. Role escalation via signup
`POST /v1/auth/signup` lets the client pass `role` in the body? Let me check.

### D5. Email enumeration via signup error
Signup with an existing email returns 409 `email_already_registered`. Login with an unknown email returns 401 `invalid_credentials` (same as wrong password). So login is safe. But signup is not — attacker can enumerate emails. Acceptable for V1.5 since most apps do this.

## E. Performance — gaps

### E1. Load baseline is SQLite, not real Postgres
The existing `docs/runbooks/load-test-baseline.md` shows numbers against in-memory SQLite. We need a fresh load test against Neon Postgres.

### E2. /home is unrowed and uncached
`GET /v1/home` runs ~8 queries (continue_watching, my_list, new_releases, trending, top_in_country, 2× BYW, 3× genre). Each unrelated; could be parallelised with `asyncio.gather`. And the global rows (new_releases, trending, top_in_country) could be cached in Redis (deferred to V2).

### E3. No query plan analysis
We have indexes on `slug`, `(status, published_at)`, etc. But I haven't run `EXPLAIN ANALYZE` on Postgres for the hot endpoints (`GET /v1/titles`, `GET /v1/home`).

### E4. Async pool size = 10 + max_overflow=20
That's 30 connections. Neon free tier allows ~100. Fine. For paid Neon (1k connections) we'd raise.

### E5. boto3 client is sync but called via lazy boto3.upload_fileobj which blocks
Uploads block the event loop. For small files OK; for 60+ minute movie uploads, the worker would be blocked. Should wrap in `run_in_threadpool` or use `aioboto3`. **Worth fixing.**

## F. Rate limiting — gaps

### F1. No rate limiting at all
The API has zero rate limits. A bot could:
- Brute-force login (slow but unbounded)
- Scrape the entire catalog by paginating
- Spam signup endpoint

For a freelance build pre-launch this is fine. Pre-prod we need:
- 5 req/s per IP on `/v1/auth/login`, `/v1/auth/signup`
- 30 req/s per user on most reads
- 200 req/s burst on public catalog reads
- Use `slowapi` (in-process) for V1.5, Redis-backed for V2

## G. Observability — gaps

### G1. No `/healthz/detailed` for ops
The existing `/healthz` does a DB ping but doesn't check storage. A storage outage would be invisible. Add: optional deep health endpoint that pings DB + storage + Razorpay.

### G2. No Sentry / error tracking
Tracebacks go to uvicorn stdout. In prod we need Sentry or equivalent. Deferred to deploy time.

### G3. No metrics endpoint
No Prometheus / metrics. Deferred.

## H. Admin upload UX — gaps

### H1. Multipart upload UX is bad
Currently you must call `POST /v1/admin/titles/{id}/upload-video` with a multipart body. Through Swagger this is clunky. A proper admin web UI would help — out of scope for backend but worth noting.

### H2. No upload progress
Backend reads the whole file then returns. For a 2GB movie that's a minute+ of waiting with no progress indicator. Phase 2: chunked uploads or signed-URL-direct-upload (frontend uploads straight to B2).

### H3. No upload size limit enforced
`_MAX_UPLOAD_BYTES = 1 GB` is defined but never checked. A malicious admin could upload a 10GB file.

### H4. No file-type validation
We accept anything with `.mp4` extension. Doesn't verify it's actually video.

## I. Webhook robustness — gaps

### I1. No replay-attack window
A captured Razorpay webhook payload, replayed days later, would still pass signature verification (it's just HMAC). Real signature schemes include a timestamp + ±5min window. Razorpay doesn't enforce this server-side but we could. Defer for V1.5.

### I2. Webhook handler under load
The webhook is processed inline. A burst of 100 webhooks would queue. Realistic Razorpay load is low (few per minute), so not a real concern.

---

## Bugs I will definitely fix

| # | Severity | Issue |
|---|---|---|
| C1 | 🔴 Critical | Expired subscriptions still grant play access |
| C3 | 🟡 High | Concurrent subscribe race — possible double-charge |
| A6 | 🟡 High | Search query with `%` returns all titles |
| H3 | 🟡 High | Upload size limit not enforced |
| B4 | 🟡 Medium | Episode play doesn't check parent series status |
| A3 | 🟡 Medium | Trailer endpoint missing |
| A2 | 🟢 Low | "Coming soon" support |
| A8 | 🟢 Low | Sort field not validated |

Plus the tests for everything in A–I that I haven't yet covered.
