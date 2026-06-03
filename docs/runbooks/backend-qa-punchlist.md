# Backend QA — synthesised punch list

**Date:** 2026-06-03
**Inputs:** my pre-research audit (`backend-qa-audit.md`) + 2 research agents (OTT flows + backend security/perf playbook)

This is the prioritised list of issues to fix before the frontend connects. Issues marked ✅ are already fixed in this commit chain. ⏳ are in progress. ⏸ are deferred to V2 with documented reason.

---

## CRITICAL — must fix before frontend wires up

| # | Issue | Status | Notes |
|---|---|---|---|
| C1 | Expired subscriptions still grant play access | ✅ Fixed | `get_my_subscription()` now also filters `current_period_end > now()` |
| C2 | Concurrent subscribe race — possible double-charge | ✅ Fixed | Idempotent pending-sub lookup; same Razorpay order returned on retry |
| C3 | Search `%` / `_` wildcards weren't escaped | ✅ Fixed | `_escape_like()` + ESCAPE clause + 100-char cap |
| C4 | Episode play didn't check parent series status | ✅ Fixed | `get_episode_by_id()` now walks up to title |
| C5 | Upload size limit defined but not enforced | ✅ Fixed | `_SizeLimitedStream` aborts mid-stream at 1 GB |
| C6 | Upload accepted any content-type | ✅ Fixed | `_validate_upload()` whitelist of video extensions + MIME types |
| C7 | Trailer endpoint missing | ✅ Fixed | `GET /v1/titles/{id}/trailer` — public, no auth |
| C8 | "Coming Soon" titles invisible | ✅ Fixed | `GET /v1/titles/coming-soon` returns scheduled titles ordered by publish_at |
| C9 | Sort field accepted arbitrary input | ✅ Fixed | Pattern-validated regex |
| C10 | boto3 sync calls block FastAPI event loop | ⏳ In progress | Wrapping all 5 boto3 calls in `run_in_threadpool` |
| C11 | Webhook handler not idempotent — duplicate Razorpay delivery double-applies | ⏳ In progress | Adding `webhook_events(event_id PK)` table |
| C12 | Webhook replay-attack window not bounded | ⏳ In progress | Reject events older than 10 min |
| C13 | Playback URL TTL is 4h — link-share window | ⏳ In progress | Reduce manifest TTL to 15 min |
| C14 | Continue Watching includes completed titles | ⏳ In progress | Filter `completed=False` by default |
| C15 | "Remove from continue" hard-deletes progress row | ⏳ In progress | Soft-hide via `hidden_from_continue` flag |
| C16 | asyncpg prepared-statement cache must be 0 for Neon pooler | ⏳ In progress | Pgbouncer in transaction mode |
| C17 | Mass-assignment on schemas — `extra="forbid"` not set | ⏳ In progress | Add to all Update schemas |
| C18 | `/readyz` separate from `/healthz` | ⏳ In progress | Liveness vs readiness split |

## HIGH — fix today (this batch)

| # | Issue | Status |
|---|---|---|
| H1 | Audit log entry on auto-promote-scheduled | ⏳ Pending |
| H2 | `first_episode_free` flag on series + episode-level entitlement | ⏳ Pending |
| H3 | Watch-progress write-throttle (only persist if >30s movement) | ⏳ Pending |
| H4 | Continue-watching dedup vs My List on /home | ⏳ Pending |
| H5 | Comprehensive BOLA test suite (user A can't read user B's data) | ⏳ Pending |
| H6 | Rate limiting on `/auth/*` (basic slowapi) | ⏳ Pending |
| H7 | Statement timeout in Postgres DSN | ⏳ Pending |
| H8 | Pagination boundary tests (page=0, page=huge) | ⏳ Pending |
| H9 | Empty-state row hiding on /home | ⏳ Pending |
| H10 | Cap response models — never leak `password_hash` (already done; add regression test) | ⏳ Pending |

## MEDIUM — deferred, but documented for V2

| # | Issue | Deferred reason |
|---|---|---|
| M1 | Geo-blocking per title/region | Single-region launch; add when client onboards international content |
| M2 | Concurrent stream / device limits | Needs stream-heartbeat infra; layer in when we have ~1k DAU |
| M3 | Kids profile / maturity filter | Needs profile sub-accounts; entire feature; V2 |
| M4 | Cursor pagination | Offset is fine for ≤10k titles; switch when catalog grows |
| M5 | Transliteration search (Hindi/Tamil → English) | Needs Elasticsearch; V2 |
| M6 | Watch-progress write-batching to Redis | Premature without 10k DAU; V2 |
| M7 | Pre-rolled hover-preview clips | Separate transcoding pipeline; V2 |
| M8 | Plan upgrades / downgrades mid-period | Single-plan launch; add when 2nd plan launches |
| M9 | Refund flow | Razorpay refund webhook + entitlement revocation; V1.6 |
| M10 | Sentry integration | Deploy-time work |
| M11 | Prometheus metrics endpoint | Deploy-time work |
| M12 | `lazy="raise"` on all relationships | Retrofit risk too high; new code uses it |

---

## What "ready for frontend" looks like

The frontend can safely wire up against this backend once all CRITICAL items are ✅ and the test suite covers them. HIGH items improve robustness but don't block the wiring up — they can be added as the frontend grows.

The DEFERRED items are real but the client doesn't need them at MVP launch. They're documented here so we don't forget them when the time comes.

## Sources

- `docs/runbooks/backend-qa-audit.md` — my pre-research audit
- `tasks/a9aae24b2214f3aa4.output` — OTT flows research transcript (full)
- `tasks/a98a1a834da5dc604.output` — Backend security/perf research transcript (full)
