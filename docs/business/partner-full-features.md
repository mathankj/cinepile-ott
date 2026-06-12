---
title: "CinePile — Full Feature Inventory"
subtitle: "Complete build status for the business partner"
author: "Engineering"
date: "2026-06-04"
---

# CinePile — Full Feature Inventory

**Audience:** business partner (internal). Shows **every** feature in the platform — built, partial, planned, and intentionally out-of-scope. No filtering, no marketing copy. Engineering's honest snapshot.

**Last updated:** 2026-06-10
**Repo:** https://github.com/mathankj/cinepile-ott (private)
**Code state:** backend 224 tests, e2e 108/108 tests (desktop), deployed locally for QA.

---

## Status legend

- ✅ **Live** — running in the code today, passes tests
- ⚠️ **Partial** — code exists but needs polish or wiring
- 📋 **Planned** — designed, not yet implemented
- ❌ **Out of scope** — deliberately not building (see "Out of scope" section)

---

## 1. Authentication & accounts

| # | Feature | Status | Notes |
|---|---|---|---|
| 1.1 | Email + password signup | ✅ | Floating-label form |
| 1.2 | Email + password sign-in | ✅ | JWT access + refresh tokens |
| 1.3 | Logout (single device) | ✅ | Clears tokens + profile |
| 1.4 | RFC-6761 reserved-TLD friendly error mapping | ✅ | Generic `.test/.example` rejected cleanly |
| 1.5 | Axios auto-refresh on 401 | ✅ | Silent re-auth, retries request once |
| 1.6 | Password reset via email | 📋 | Needs Mailgun (free tier OK) |
| 1.7 | Email verification | 📋 | Needs Mailgun |
| 1.8 | Google social login | 📋 | Needs Google Cloud OAuth credentials |
| 1.9 | Apple sign-in | 📋 | Needs Apple Developer membership |
| 1.10 | Profile PIN / lock | 📋 | Backend column + UI |
| 1.11 | Account settings (change email/password/delete account) | ⚠️ | Account page + change-password shipped 2026-06-10 (revokes other sessions); change-email + delete-account still pending (DPDPA) |
| 1.12 | Cross-device session list / "log out everywhere" | 📋 | Refresh-token table query |
| 1.13 | Two-factor (2FA) | ❌ | Out of V1; security overhead vs OTT user benefit is low |
| 1.14 | Session token rotation on refresh | ✅ | Backend rotates refresh tokens automatically |

---

## 2. Profiles ("Who's watching?")

| # | Feature | Status | Notes |
|---|---|---|---|
| 2.1 | Profile picker screen on login | ✅ | Netflix-style 2×2 grid |
| 2.2 | Profile auto-create on signup | ✅ | First profile is the user's full name |
| 2.3 | 4 profiles per account hard cap | ✅ | Matches Netflix Standard tier |
| 2.4 | Avatar picker (emoji grid) | ✅ | 16 options; expandable |
| 2.5 | Kid profile flag (adult/kid kind) | ✅ | Enforced since 2026-06-10 — see 2.11 |
| 2.6 | Profile edit (name, avatar, kind) | ✅ | Modal with form |
| 2.7 | Profile delete (non-primary only) | ✅ | Primary cannot be removed |
| 2.8 | Active-profile persistence | ✅ | Zustand + localStorage with hydration handling |
| 2.9 | Switch profile via navbar | ✅ | Dropdown in profile menu |
| 2.10 | Profile-scoped continue-watching + watchlist + reactions | ✅ | Shipped 2026-06-10 — `profile_id` migration, `X-Profile-Id` header, per-profile home rows; pre-profile data stays reachable |
| 2.11 | Kid mode content filter (U-rated only) | ✅ | Shipped 2026-06-10 — U-rated-only home rows + hard server-side playback block (403). Known gap: browse/search not yet kid-filtered (playback always is) |
| 2.12 | Profile PIN / lock | 📋 | Backend column + UI |
| 2.13 | Profile transfer between users | ❌ | Not a real OTT feature |

---

## 3. Home / Discovery

| # | Feature | Status | Notes |
|---|---|---|---|
| 3.1 | Billboard hero (backdrop + Play + Info CTAs) | ✅ | With deterministic gradient fallback when no art |
| 3.2 | Hero entrance animation (scale + fade) | ✅ | Framer Motion |
| 3.3 | Continue Watching row | ✅ | Cache-busts on every progress write |
| 3.4 | My List row | ✅ | Cache-busts on watchlist add/remove |
| 3.5 | New Releases row | ✅ | Backend window: last 30 days |
| 3.6 | Trending Now row | ✅ | view_count desc (proxy for trending) |
| 3.7 | Top in country row | ✅ | `?country=IN` query param |
| 3.8 | Recommended for You row | ✅ | Seeded by thumbs-up + watchlist + history |
| 3.9 | Because You Watched X row(s) | ✅ | Cap 2 rows; seeded by finished titles |
| 3.10 | Genre rows from user's top genres | ✅ | Auto-derived from history |
| 3.11 | Home page server-side cache (60s TTL) | ✅ | Per-user; auto-invalidated on writes |
| 3.12 | Skeleton shimmer while loading | ✅ | Site-wide style class |
| 3.18 | "More Like This" (similar titles) row on title detail | ✅ | Added 2026-06-10 — `GET /v1/titles/{id}/similar`, shared-genre, most-watched first |
| 3.13 | Trailer auto-play on hover (Netflix-iconic mini-trailer) | 📋 | Phase 2 |
| 3.14 | Top 10 in India daily-refreshed row | 📋 | Phase 2 |
| 3.15 | Watch Again row (completed titles) | 📋 | Phase 2 |
| 3.16 | Editorial / curated collections | 📋 | Phase 3 (admin tool needed) |
| 3.17 | ML-based recommendation engine | 📋 | Phase 3 |

---

## 4. Browse / Search

| # | Feature | Status | Notes |
|---|---|---|---|
| 4.1 | /browse with type / genre / sort filters | ✅ | URL state, deep-linkable |
| 4.2 | Type filter dropdown (All / Movies / TV Shows) | ✅ | Added in QA pass |
| 4.3 | Genre dropdown from /v1/home/genres | ✅ | 5 genres seeded |
| 4.4 | Sort: Newest, Oldest, A→Z, Z→A, Most watched | ✅ | |
| 4.5 | Pagination (Prev/Next) | ✅ | Disabled at boundary |
| 4.6 | Empty-state message | ✅ | "No titles match. Try clearing filters." |
| 4.7 | Search with 300ms debounce | ✅ | |
| 4.8 | 2-char minimum guard | ✅ | UI hint |
| 4.9 | LIKE-escape (% and _ are literal, not wildcards) | ✅ | SQL safety |
| 4.10 | Search-result highlighting | 📋 | Phase 2 |
| 4.11 | Search history / recent searches | 📋 | Phase 3 |
| 4.12 | Voice search | ❌ | Out of scope |

---

## 5. Title detail / Series detail / Episodes

| # | Feature | Status | Notes |
|---|---|---|---|
| 5.1 | Title detail page (movie + series) | ✅ | Synopsis, cast, genres, age, runtime |
| 5.2 | Play button (movies) / Play S1E1 (series) | ✅ | |
| 5.3 | More Info / Add to My List buttons | ✅ | |
| 5.4 | Watch Trailer button | ✅ | Plays **in-app** (`/watch/trailer/:id`) since 2026-06-10; backed by `trailer_url` |
| 5.5 | Three-state reaction (thumbs up/down/double-up) | ✅ | |
| 5.6 | Episode list per season | ✅ | Per-season tabs |
| 5.7 | Episode runtime + intro markers | ✅ | |
| 5.8 | Hover-prefetch detail data | ✅ | Cards prefetch detail query on hover |
| 5.9 | Card hover overlay (Play/+/Info icon buttons) | ✅ | Real handlers; keyboard-accessible |
| 5.10 | Backwards-compat title-by-slug lookup | ⚠️ | Old `the-anjaneya-chronicles` slug aliased |
| 5.11 | User reviews / ratings | 📋 | Phase 3 (needs moderation) |
| 5.12 | Cast bio pages | 📋 | Phase 3 |
| 5.13 | Episode lazy-load past S5 (long series) | 📋 | Phase 2 |
| 5.14 | Trailer auto-play (muted, 30s) on title detail | 📋 | Phase 2 |

---

## 6. Video player

| # | Feature | Status | Notes |
|---|---|---|---|
| 6.1 | HLS playback via hls.js | ✅ | Chrome/Firefox/Edge |
| 6.2 | Native HLS playback (Safari) | ✅ | iOS + macOS |
| 6.3 | Direct MP4 fallback | ✅ | When source isn't `.m3u8` |
| 6.4 | Adaptive bitrate (auto quality) | ✅ | hls.js default ABR |
| 6.5 | Manual quality picker (Auto / 1080p / 720p / 480p / …) | ✅ | Settings gear top-right |
| 6.6 | Multi-audio track switcher | ✅ | Populates from manifest `EXT-X-MEDIA TYPE=AUDIO` |
| 6.7 | Multi-subtitle / CC switcher | ✅ | Sidecar `.vtt` + in-manifest both supported |
| 6.8 | Skip Intro overlay | ✅ | Episode markers `intro_start_sec`/`intro_end_sec` |
| 6.9 | Resume from last position | ✅ | Per-user, per-title |
| 6.10 | Progress reporting (every 10s + on pause) | ✅ | |
| 6.11 | Cosmetic anti-capture shield | ✅ | Right-click block, controlsList=nodownload, tab-hidden curtain |
| 6.12 | Skip Recap overlay | ✅ | Shipped 2026-06-10 — episode `recap_start_sec`/`recap_end_sec` markers, editable in the admin Seasons editor |
| 6.13 | Next-Episode auto-advance with countdown | ✅ | Shipped 2026-06-10 — 10 s countdown overlay, Cancel/Play Now |
| 6.14 | Manual quality cap toggle ("Use less data") | 📋 | Phase 2 |
| 6.15 | Picture-in-picture | 📋 | Phase 3 (currently disabled for anti-capture) |
| 6.16 | Chromecast / Google Cast | 📋 | Phase 2 |
| 6.17 | AirPlay | 📋 | Phase 3 |
| 6.18 | Real DRM (Widevine + PlayReady + FairPlay) | ⚠️ | Client-side EME scaffolded; needs license-server contract |
| 6.19 | Downloads for offline | 📋 | Phase 2 (requires 6.18 first) |
| 6.20 | 4K HDR playback | 📋 | Phase 3 (needs catalog + CDN scale) |
| 6.21 | Dolby Vision / Dolby Atmos | 📋 | Phase 3 (needs Dolby license) |

---

## 7. Subscription & billing

| # | Feature | Status | Notes |
|---|---|---|---|
| 7.1 | /subscribe page with plan list | ✅ | |
| 7.2 | Razorpay Orders mode | ✅ | One-time payment per billing period |
| 7.3 | Razorpay test-checkout HTML helper | ✅ | Dev only |
| 7.4 | Subscription states (active / pending / cancelled) | ✅ | |
| 7.5 | 402 paywall on paid content with View Plans CTA | ✅ | |
| 7.6 | Free titles bypass subscription (`is_free` flag) | ✅ | |
| 7.7 | Cancel at period end | ✅ | |
| 7.8 | Webhook idempotency (no duplicate sub on retry) | ✅ | `webhook_events` table |
| 7.9 | Razorpay Subscriptions mode (recurring) | ⚠️ | Code present; KYC required to enable |
| 7.10 | Tier ladder: Mobile / Standard / Premium | 📋 | Phase 2 |
| 7.11 | Simultaneous-stream enforcement per tier | 📋 | Phase 2 |
| 7.12 | Device limit per tier (1 / 2 / 4) | 📋 | Phase 2 |
| 7.13 | Annual discount bump (17% → 33%) | 📋 | Phase 2; config change |
| 7.14 | Promo codes / discount campaigns | 📋 | Phase 3 |
| 7.15 | Gift subscriptions | 📋 | Phase 3 |
| 7.16 | Family plan (multi-email shared) | 📋 | Phase 3 |
| 7.17 | AVOD (free tier with ads) | 📋 | Phase 3 |
| 7.18 | Pay-per-view (TVOD) | ❌ | Out of scope |

---

## 8. Multi-language / i18n

| # | Feature | Status | Notes |
|---|---|---|---|
| 8.1 | i18next + react-i18next | ✅ | |
| 8.2 | Language picker in navbar (globe icon) | ✅ | |
| 8.3 | LocalStorage persistence | ✅ | Survives reload |
| 8.4 | Browser language auto-detect on first visit | ✅ | |
| 8.5 | English UI | ✅ | Full coverage incl. player — 187 keys (2026-06-10 sweep, up from 94) |
| 8.6 | Hindi UI | ✅ | Full coverage, same 187 keys |
| 8.7 | Tamil UI | ✅ | Full coverage, same 187 keys |
| 8.8 | Telugu / Kannada / Malayalam / Bengali UI | 📋 | Phase 2 (add JSON files) |
| 8.9 | Subtitle (.vtt) sidecar upload per language | ✅ | Admin endpoint |
| 8.10 | In-manifest subtitle tracks | ✅ | Player auto-discovers |
| 8.11 | Multi-language title metadata (per-title translations) | 📋 | Phase 3 (schema change) |
| 8.12 | Auto-translated subtitles via Whisper | 📋 | Phase 3 |
| 8.13 | Auto-dubbed audio (AI) | 📋 | Phase 3 |
| 8.14 | Multi-audio track upload | ❌ | Browser limitation; multi-audio must come from producer HLS |

---

## 9. Admin / content management

| # | Feature | Status | Notes |
|---|---|---|---|
| 9.1 | Admin login (role-gated) | ✅ | Role: admin / content_manager / user |
| 9.2 | Admin dashboard with stats | ✅ | |
| 9.3 | Admin titles list with filter + search | ✅ | Includes drafts |
| 9.4 | Create new title (movie or series) | ✅ | |
| 9.5 | Edit title metadata (everything except slug after create) | ✅ | |
| 9.6 | Publish / schedule / archive workflow | ✅ | |
| 9.7 | Soft-delete with restore | ✅ | Restore endpoint + admin "Deleted" tab with one-click restore shipped 2026-06-10 (before that only the `deleted_at` column existed — no way to restore). Restores to `archived`, never auto-publishes |
| 9.8 | Video upload (multipart streamed to B2) | ✅ | 1 GB cap |
| 9.9 | Magic-byte sniff (ISO BMFF / WebM / HLS validation) | ✅ | Defense against renamed EXE |
| 9.10 | Subtitle (.vtt) upload per language | ✅ | 5 MB cap, upsert by language |
| 9.11 | Subtitle remove (DB row only; object retained for undo) | ✅ | |
| 9.12 | Audio track management UI | ⚠️ | Backend endpoint exists; admin UI not yet exposed |
| 9.13 | Per-episode video upload | ✅ | Admin UI (Seasons editor upload cards with progress bar) shipped 2026-06-10; endpoint existed before |
| 9.14 | Per-episode subtitle upload | ✅ | Same — upload UI in the Seasons editor since 2026-06-10 |
| 9.15 | Season + episode create | ✅ | Full Seasons/Episodes editor UI (metadata, skip markers, publish/delete) since 2026-06-10 |
| 9.16 | Genre management | ✅ | Full CRUD since 2026-06-10 — dedicated admin Genres page, rename + delete (delete blocked while in use) |
| 9.17 | Admin-scoped detail endpoint for drafts | ✅ | Fixes "editor blank for new title" bug |
| 9.18 | User management (list, change role) | ✅ | Admin-only |
| 9.19 | Audit log (who/what/when/before/after) | ✅ | Filterable |
| 9.20 | Bulk operations (delete N, publish N) | 📋 | Phase 3 |
| 9.21 | Editorial collection builder | 📋 | Phase 3 |
| 9.22 | Content moderation / takedown workflow | 📋 | Phase 3 |
| 9.23 | Title import from CSV / API | 📋 | Phase 3 |

---

## 10. Watch progress / history

| # | Feature | Status | Notes |
|---|---|---|---|
| 10.1 | Movie progress save | ✅ | Per-user |
| 10.2 | Episode progress save | ✅ | |
| 10.3 | Resume from last position on next play | ✅ | |
| 10.4 | Continue Watching list (collapsed by series) | ✅ | |
| 10.5 | Completion threshold (~95%) marks as completed | ✅ | |
| 10.6 | "Remove from Continue Watching" | ✅ | |
| 10.7 | Full viewing history page | ✅ | Paginated |
| 10.8 | Delete from history | ✅ | |
| 10.9 | Export viewing history | 📋 | Phase 3 (DPDPA compliance) |

---

## 11. Watchlist / My List

| # | Feature | Status | Notes |
|---|---|---|---|
| 11.1 | Add to My List | ✅ | Idempotent |
| 11.2 | Remove from My List | ✅ | |
| 11.3 | My List page with shimmer + empty state | ✅ | Includes CTA to /browse |
| 11.4 | + button on card flips to ✓ when on list | ✅ | |
| 11.5 | My List filter + sort | 📋 | Phase 2 |

---

## 12. Reactions

| # | Feature | Status | Notes |
|---|---|---|---|
| 12.1 | Thumbs up | ✅ | |
| 12.2 | Thumbs down | ✅ | |
| 12.3 | Double thumbs up ("love") | ✅ | |
| 12.4 | Reaction history (`/v1/me/reactions`) | ✅ | |
| 12.5 | Reactions used as recommendation seeds | ✅ | Fixed in QA pass (was filtering on non-existent `kind="like"`) |
| 12.6 | Public ratings aggregate | ❌ | Netflix doesn't do this; we follow |

---

## 13. Frontend infrastructure

| # | Feature | Status | Notes |
|---|---|---|---|
| 13.1 | React 19 + Vite + TypeScript + Tailwind v4 | ✅ | |
| 13.2 | React Router 7 with lazy-loaded routes | ✅ | Per-route code splitting |
| 13.3 | TanStack Query for server state | ✅ | |
| 13.4 | Zustand for auth + profile state | ✅ | With persist + hydration handling |
| 13.5 | Framer Motion animations | ✅ | Billboard entrance, row stagger, card hover |
| 13.6 | Responsive design (5 viewports tested) | ✅ | 360 / 414 / 768 / 1280 / 1920 |
| 13.7 | Mobile + tablet drawer (hamburger) | ✅ | Slides from right |
| 13.8 | Skeleton shimmer site-wide | ⚠️ | Home + MyList have it; other pages still "Loading…" |
| 13.9 | Error toasts on API failures | 📋 | Currently silent on /admin/users 500 |
| 13.10 | Dark mode (default, OTT-style) | ✅ | |
| 13.11 | Light mode toggle | ❌ | Out of scope for OTT |
| 13.12 | Service worker / PWA | 📋 | Phase 3 |

---

## 14. Backend infrastructure

| # | Feature | Status | Notes |
|---|---|---|---|
| 14.1 | FastAPI async | ✅ | |
| 14.2 | SQLAlchemy 2.0 async ORM | ✅ | |
| 14.3 | Postgres (Neon for dev) | ✅ | |
| 14.4 | Alembic migrations | ✅ | |
| 14.5 | Backblaze B2 storage with presigned URLs | ✅ | |
| 14.6 | S3-compatible storage abstraction (R2, AWS, Storj) | ✅ | Works with any S3 endpoint |
| 14.7 | JWT auth with rotation | ✅ | |
| 14.8 | Audit logging service | ✅ | Every admin action logged |
| 14.9 | Webhook idempotency | ✅ | `webhook_events` table with seen-id check |
| 14.10 | Health + readyz endpoints | ✅ | |
| 14.11 | Razorpay client (Orders + Subscriptions modes) | ✅ | Subscriptions mode pending KYC |
| 14.12 | Rate limiting | ✅ | Shipped 2026-06-10 — login (10/min) + signup (5/min) per client IP, in-process sliding window. Redis-keyed swap needed when scaling past one worker |
| 14.13 | Background job queue (Celery / RQ / Arq) | 📋 | Phase 3 |
| 14.14 | Email service abstraction | 📋 | Phase 2 (Mailgun) |
| 14.15 | DRM token signing service | ✅ | Code path; activated when provider configured. Fails closed if `DRM_TOKEN_SECRET` missing (never falls back to the app JWT secret) |
| 14.16 | Search service | ✅ | **LIKE-based** (case-insensitive, wildcard-escaped, 100-char cap) — NOT Postgres full-text. tsvector upgrade planned when the catalog scales (see 14.17) |
| 14.17 | Elasticsearch / Meilisearch (better search) | 📋 | Phase 3 |
| 14.18 | CORS configured | ✅ | |
| 14.19 | Request ID logging | ✅ | |
| 14.20 | Structured logging (JSON) | ✅ | structlog |
| 14.21 | Security headers (nosniff, X-Frame-Options DENY, Referrer-Policy, HSTS in prod) | ✅ | Added 2026-06-10 |
| 14.22 | Gzip response compression | ✅ | Added 2026-06-10 — JSON >500 bytes |
| 14.23 | Payment capture + amount verification before activating subs | ✅ | Added 2026-06-10 — signature alone no longer unlocks access |

---

## 15. Testing & quality

| # | Feature | Status | Notes |
|---|---|---|---|
| 15.1 | Backend pytest suite (integration + unit) | ✅ | 224 tests (was 144) — security hardening, profile scoping, similar titles, admin features, query-efficiency suites added 2026-06-10 |
| 15.2 | Backend load tests (Locust) | ⚠️ | Baseline recorded; not in CI |
| 15.3 | Frontend Playwright e2e | ✅ | 108/108 desktop, 31/95 mobile (skips are by design) |
| 15.4 | Role × route access matrix tests | ✅ | 56 access checks |
| 15.5 | Visual responsive audit screenshots | ✅ | All 5 viewports captured |
| 15.6 | Real upload e2e (B2 round-trip + presigned URL verify) | ✅ | |
| 15.7 | Subtitle upload e2e (4 tests) | ✅ | |
| 15.8 | i18n switch + persist e2e | ✅ | |
| 15.9 | CI/CD pipeline (GitHub Actions) | 📋 | Phase 2 |
| 15.10 | Production smoke tests | 📋 | After Phase 1 deploy |
| 15.11 | Performance budget tests (LCP, CLS, INP) | 📋 | Phase 3 |
| 15.12 | A11y automated tests (axe-core) | 📋 | Phase 2 |

---

## 16. Infrastructure & ops

| # | Feature | Status | Notes |
|---|---|---|---|
| 16.1 | Local dev Docker Compose | ❌ | Not provided; npm + python venv only |
| 16.2 | Production deployment runbook | ⚠️ | Documented; not yet executed |
| 16.3 | Database backup strategy | 📋 | Phase 2 (Neon has point-in-time but documented) |
| 16.4 | Multi-region CDN (Bunny / Cloudflare) | 📋 | Phase 2 (single-region works for V1) |
| 16.5 | Transcoding pipeline (MediaConvert) | 📋 | Phase 3 |
| 16.6 | Status page (statuspage.io / Statuspage) | 📋 | Phase 3 |
| 16.7 | Monitoring (Sentry) | 📋 | Phase 2 (free tier OK) |
| 16.8 | Product analytics (PostHog) | 📋 | Phase 2 |
| 16.9 | Uptime monitoring (Better Uptime / Pingdom) | 📋 | Phase 2 |
| 16.10 | Blue-green deployment | 📋 | Phase 3 |
| 16.11 | Auto-scaling | 📋 | Phase 3 (Contabo vertical-scale fine for now) |
| 16.12 | Database replicas | 📋 | Phase 3 |
| 16.13 | Forensic watermark (invisible) | 📋 | Phase 3 (₹15k+/mo) |
| 16.14 | Anti-piracy monitoring | 📋 | Phase 3 |

---

## 17. Native apps & TV

| # | Feature | Status | Notes |
|---|---|---|---|
| 17.1 | iOS native app | 📋 | Phase 3 (8-12 weeks) |
| 17.2 | Android native app | 📋 | Phase 3 (8-12 weeks) |
| 17.3 | Samsung Tizen TV app | 📋 | Phase 3 |
| 17.4 | LG webOS TV app | 📋 | Phase 3 |
| 17.5 | Android TV / Google TV | 📋 | Phase 3 |
| 17.6 | Apple TV app | 📋 | Phase 3 |
| 17.7 | Roku app | 📋 | Phase 3 (India market: small) |
| 17.8 | Amazon Fire TV | 📋 | Phase 3 |

---

## 18. Social / community

| # | Feature | Status | Notes |
|---|---|---|---|
| 18.1 | Reactions (thumbs) | ✅ | Per-user, not public |
| 18.2 | Group Watch / Watch Party | 📋 | Phase 3 |
| 18.3 | Activity sharing ("I just watched X") | 📋 | Phase 3 (opt-in) |
| 18.4 | User reviews + ratings | 📋 | Phase 3 (needs moderation) |
| 18.5 | Follow other users | ❌ | Not an OTT feature |
| 18.6 | Comments per title | ❌ | Toxic without heavy moderation |

---

## 19. Legal / compliance

| # | Feature | Status | Notes |
|---|---|---|---|
| 19.1 | GDPR / DPDPA data export | 📋 | Phase 3 |
| 19.2 | Account deletion with data removal | 📋 | Phase 3 |
| 19.3 | Cookie consent banner | 📋 | Phase 2 (EU users, even one) |
| 19.4 | Terms of Service page | 📋 | Phase 1 (footer link exists; page empty) |
| 19.5 | Privacy Policy page | 📋 | Phase 1 |
| 19.6 | Cookie Policy page | 📋 | Phase 1 |
| 19.7 | Content rating per region | 📋 | Phase 3 (CBFC + age-rating per market) |
| 19.8 | Geographic content restrictions | 📋 | Phase 3 (CDN geo-block) |

---

## Out of scope (we will NOT build, even if asked)

| Feature | Reason |
|---|---|
| Live sports / IPL | Hotstar's moat — rights ₹400+ cr/yr |
| Voice search | Indian-accent English voice recognition is rough |
| Smart-speaker integration | Niche for video |
| Cloud DVR for live | Premature; no live yet |
| Pay-per-view (TVOD) | Doesn't fit SVOD model |
| Two-factor auth (2FA) | Overhead vs benefit low for OTT |
| Light mode toggle | OTT is dark by default |
| Real-time comments per title | Moderation cost too high |
| Follow other users | Not a streaming feature |

---

## Summary table

| Status | Count |
|---|---|
| ✅ Live | 113 features |
| ⚠️ Partial | 7 features |
| 📋 Planned | ~79 features |
| ❌ Out of scope | 9 features |
| **Total inventoried** | **~208 features** |

(2026-06-10 flips: profile scoping, kid filter, skip-recap, auto-advance, rate limiting → ✅; account settings 📋 → ⚠️; new rows for More Like This, security headers, gzip, payment capture check.)

---

## Where to find what

| Doc | Purpose |
|---|---|
| `docs/business/partner-full-features.md` | This file (full inventory for partner) |
| `docs/business/client-pitch.md` | Phased pitch deck for client meeting |
| `docs/qa/FINAL-REPORT.md` | QA findings + cost decisions for client |
| `docs/qa/competitive-analysis.md` | Indian OTT market analysis |
| `docs/decisions/0003-drm.md` | DRM provider comparison + ADR |
| `docs/api/v1.md` | API contract |
| `docs/db-schema.md` | Database schema reference |

Repo: https://github.com/mathankj/cinepile-ott (private)
