# Netflix parity coverage matrix

The exhaustive checklist used for QA. Every Netflix flow / UX pattern is one
row. Three statuses:

- ✅ **Have**: implemented + covered by an e2e test.
- ⚠️  **Partial**: implemented but rough, or missing a test.
- ❌ **Gap**: not implemented yet (or genuinely out of scope — see Notes).

Rule for promotion to ✅: feature exists, works in dev, AND has at least one
e2e or backend test that would fail if it broke.

## Top-level navigation

| Area | Pattern | Status | Notes |
|---|---|---|---|
| Nav | Sticky top bar, transparent over hero, solid on scroll>60px | ✅ | `Navbar.tsx`, e2e `home.spec.ts` |
| Nav | Brand → Home, primary links (Home, TV, Movies, New & Popular) | ✅ | Active link bolded |
| Nav | Search icon → /search | ✅ | |
| Nav | Notifications icon | ⚠️ | UI only, no real notification system |
| Nav | Profile menu with My List, History, Subscription, Sign out | ✅ | `auth.spec.ts` logout test |
| Nav | Mobile hamburger drawer with all links | ✅ | `mobile.spec.ts` |
| Nav | "Kids" profile mode | ✅ | Kid profiles (kind="kid") get U-rated-only home rows + a hard server-side playback block (403 `kid_profile_restricted`). Gap: catalog browse/search not yet kid-filtered — playback is the hard gate |
| Nav | Search modal overlay (Netflix-style) instead of separate page | ❌ | We use /search route — equivalent UX |

## Home page

| Pattern | Status | Notes |
|---|---|---|
| Hero billboard with backdrop + title + Play/More Info | ✅ | `Billboard.tsx`, entrance animation |
| Multiple title rows (New Releases, Trending, etc.) | ✅ | `/v1/home` returns rows |
| Continue Watching row (logged-in only) | ✅ | `progress.continueWatching()` |
| My List row (logged-in only) | ⚠️ | Backend yes; UI rows on home — needs row in `/v1/home` |
| Top 10 in your country | ❌ | Out of V1 |
| Genre-based rows (Romance / Action) | ⚠️ | Backend supports; not exposed on home yet |
| Horizontal scroll with arrows on hover | ✅ | `TitleRow.tsx` |
| Card hover-reveal with Play/+/Info overlay | ✅ | `TitleCard.tsx`, `subscribe-trailer.spec.ts` |
| Hover image upscale (scale 1.08, ~300ms ease) | ✅ | Framer Motion |
| Lazy-load card images (`loading="lazy"`) | ✅ | |
| Auto-playing preview-video on hover (Netflix mini-trailer) | ❌ | Real Netflix uses pre-encoded preview clips; out of V1 |

## Title detail

| Pattern | Status | Notes |
|---|---|---|
| Full backdrop hero | ✅ | |
| Play / More info CTAs | ✅ | |
| Synopsis + cast + genres | ✅ | `TitleDetail.tsx` |
| Episode list for series with season tabs | ✅ | `Season.tsx`, `title-detail.spec.ts` |
| Watch Trailer button (when configured) | ✅ | Plays **in-app** at `/watch/trailer/:id` (public endpoint, no ticket needed); returns to the title page when finished |
| Similar titles row at bottom | ✅ | "More Like This" — `GET /v1/titles/{id}/similar`, shared-genre, view_count desc; backend tests in `test_similar_titles.py` |
| Rating system (thumb up/down, two-thumbs) | ✅ | `me.setReaction()` |
| Add to My List | ✅ | `me.addToList()` |

## Watch / playback

| Pattern | Status | Notes |
|---|---|---|
| HLS streaming via hls.js + native fallback | ✅ | `VideoPlayer.tsx` |
| Adaptive bitrate (auto quality) | ✅ | hls.js default |
| Manual quality picker (Auto / 1080p / 720p / …) | ✅ | Settings gear |
| Audio track switcher (multi-language) | ✅ | Settings gear |
| Subtitle track switcher (Off / language) | ✅ | Settings gear |
| Resume from last position | ✅ | `playback.resume_at_sec` |
| Skip-intro overlay | ✅ | `VideoPlayer.tsx` |
| Skip-recap overlay | ✅ | Renders from `recap_start_sec`/`recap_end_sec`; markers editable in the admin Seasons editor |
| Next-episode auto-advance | ✅ | 10 s "Next episode in N…" countdown overlay with Cancel / Play Now; resolves the next episode across season boundaries |
| Picture-in-picture | ❌ (intentionally disabled by anti-capture cosmetic) |
| Download for offline | ❌ | Out of V1 — requires DRM |
| Right-click / contextmenu block | ✅ | `Watch.tsx` |
| `controlsList="nodownload"` on `<video>` | ✅ | |
| Tab-hidden "Protected content" curtain | ✅ | |
| Real DRM (Widevine/PlayReady/FairPlay) | ❌ | Requires DRM provider — separate ADR pending. **Until done, content is not truly protected.** |

## Auth

| Pattern | Status | Notes |
|---|---|---|
| Sign In with hero background + glass card | ✅ | `AuthShell.tsx`, `Login.tsx` |
| Sign Up with same shell | ✅ | `Signup.tsx` |
| Floating-label inputs (Netflix-style) | ✅ | `.input-auth` |
| Remember me checkbox | ⚠️ | UI only; doesn't actually change refresh-token TTL yet |
| Forgot password | ❌ | Needs SMTP. See "Password reset wiring" below before starting. |
| Social login (Google/FB) | ❌ | Needs Google/Apple OAuth credentials. See "Social login wiring" below. |
| Email verification | ❌ | Needs SMTP (same wiring as password reset). |
| Session token rotation on refresh | ✅ | Backend issues new pair on each refresh |
| Logout invalidates session | ✅ | `clear()` + backend logout endpoint |
| Redirect back to original URL after login | ✅ | `subscribe-trailer.spec.ts` |
| 401 → silent refresh, then retry | ✅ | `client.ts` interceptor |

## Subscribe / billing

| Pattern | Status | Notes |
|---|---|---|
| /subscribe lists plans (Monthly / Annual) | ✅ | `Subscribe.tsx`, `subscribe-trailer.spec.ts` |
| Plan picker shows currency (₹) + cadence | ✅ | |
| Razorpay Orders flow with test-checkout helper | ✅ | Backend `razorpay_client.py` |
| Subscription state (active / pending / cancelled) | ✅ | `subQ.data.status` |
| Cancel at period end | ✅ | `cancelM` mutation |
| 402 "subscription required" on paid play | ✅ | `title-detail.spec.ts` |
| Free titles bypass subscription | ✅ | `is_free` flag |
| Coupon / discount codes | ❌ | Out of V1 |
| Family / shared accounts | ❌ | Out of V1 |
| Multiple profiles per account | ✅ | Real per-profile scoping (watchlist / progress / reactions / home rows) via `X-Profile-Id` header; 4 profiles per account, kid profiles enforced |

## Browse / search

| Pattern | Status | Notes |
|---|---|---|
| /browse?type=movie filter | ✅ | `browse-search.spec.ts` |
| /browse?type=series filter | ✅ | |
| Genre dropdown populated from API | ✅ | |
| Sort by newest / oldest / A-Z / Z-A / most-watched | ✅ | `Browse.tsx` |
| Pagination | ✅ | |
| Search debounced 300ms | ✅ | `Search.tsx` |
| Search rejects <2 chars | ✅ | |
| LIKE-escape (% is literal, not wildcard) | ✅ | Backend test + e2e |
| Search highlights matched terms | ❌ | Out of V1 |
| Search history / recent searches | ❌ | Out of V1 |

## Admin

| Pattern | Status | Notes |
|---|---|---|
| /admin role-gated (admin + content_manager) | ✅ | `access-matrix.spec.ts` covers all 4 personas × 14 routes |
| /admin/users (admin only) | ✅ | |
| /admin/audit (admin only) | ✅ | |
| Title list with edit links | ✅ | `admin.spec.ts` |
| New title editor form | ✅ | `admin.spec.ts` |
| Upload video (.mp4) per title | ⚠️  | Endpoint works; e2e test SKIPS when storage unconfigured (`admin-upload.spec.ts`). **Requires B2/R2/S3 creds in `backend/.env`.** |
| Per-episode video upload | ⚠️ | Same storage gating |
| Publish / schedule / archive workflow | ✅ | |
| Soft-delete with restore | ✅ | `deleted_at` column |
| Audit log with actor / action / before-after | ✅ | `audit_svc` |
| Role change (admin only) | ✅ | |
| Bulk operations | ❌ | Out of V1 |

## Recommendations

| Pattern | Status | Notes |
|---|---|---|
| Personal recommendation row | ❌ | Out of V1 — no recommendation engine |
| "Because you watched X" | ❌ | Out of V1 |
| Collaborative filtering | ❌ | Out of V1 |
| Editorial / curated rows | ⚠️ | Backend supports `home_row` table; only New/Trending seeded |
| Trending Now (view-count based) | ✅ | `/v1/home` row |
| New Releases | ✅ | |

## Accessibility / polish

| Pattern | Status | Notes |
|---|---|---|
| WCAG-AA color contrast | ✅ | Design tokens |
| Keyboard navigation (Tab through cards) | ⚠️ | Focus rings on cards; not all interactive elements verified |
| Screen reader landmarks (banner / main / contentinfo) | ✅ | `AppLayout.tsx` |
| Alt text on all imagery | ✅ | |
| Reduced motion respected | ❌ | No `prefers-reduced-motion` handling — should be added |
| Focus-visible outlines | ✅ | Card focus ring |

## Performance

| Pattern | Status | Notes |
|---|---|---|
| Route-level code splitting | ✅ | `React.lazy()` per route |
| Hover-prefetch title detail | ✅ | `TitleCard.tsx` |
| Image lazy-loading | ✅ | `loading="lazy"` |
| HTTP cache headers on static | ⚠️ | Vite handles dev; prod nginx config needed |
| HLS chunk pre-loading | ✅ | Tuned 2026-06-10: `startFragPrefetch: true` + buffer limits; vendor-hls split into its own lazy chunk (entry bundle 522 KB → 33 KB) with hover-prefetch of the Watch chunk |

## Internationalisation

| Pattern | Status | Notes |
|---|---|---|
| UI translation (i18n) | ✅ | i18next + EN/HI/TA, language picker in navbar (globe icon), persisted to localStorage. Full coverage incl. player since 2026-06-10 (187 keys ×3 locales). Adding a 4th language = drop a JSON file + register in `src/i18n/index.ts`. |
| Multi-language metadata (title / synopsis) | ⚠️ | Backend has `original_language`; no localised strings table yet. Phase 2 if marketing needs Hindi/Tamil synopses. |
| Per-region content filtering | ⚠️ | `/v1/home?country=IN` accepts param; not exposed in UI |
| Subtitle / dub language picker (in-manifest) | ✅ | Player settings gear (hls.js audioTracks + subtitleTracks) |
| Sidecar subtitle upload (.vtt per language) | ✅ | Admin can upload one .vtt per language; player attaches as `<track>` |

## What's strictly out of V1 (and you should know now)

These all need significant new work and most need ongoing $$:

1. **Real DRM** — Widevine/PlayReady/FairPlay license server + encryption pipeline. Without this, content is technically copyable. (Token signing + EME scaffolding exist; needs a license-server contract.)
2. ~~**Profiles**~~ — **DONE 2026-06-10**: per-profile watchlist/progress/reactions/home rows + kid enforcement.
3. **Recommendation engine** — collaborative filtering or ML-based rec rows. Needs data + a service. (Genre-similarity "More Like This" + seeded rows exist; real ML does not.)
4. **Downloads for offline** — requires DRM + client-side DRM session storage.
5. **Live events / sports** — different infra entirely (low-latency HLS / LL-DASH).
6. **Native mobile apps** — current product is web-only.
7. **Password reset email** — needs SMTP / SES / Sendgrid wiring.
8. **Social login** — Google / Apple / Facebook OAuth.
9. ~~**i18n**~~ — **DONE**: full EN/HI/TA coverage incl. player (187 keys ×3 locales as of 2026-06-10).

If any of these are on the original client deliverable, flag them NOW so we
can scope a phase 2 contract.

---

## Password reset wiring (when you're ready)

What you need: an SMTP provider, ~30 min of eng time.

1. Pick a provider — any of these work; all have free tiers:
   - **AWS SES** — cheapest at scale, ~₹7 per 1000 emails. Free tier 62k/mo from EC2.
   - **Sendgrid** — 100/day free, simple Python SDK.
   - **Postmark** — 100/mo free, best deliverability in this list.
   - **Resend** — 3000/mo free, easiest API.

2. Backend changes (file paths for reference):
   - `app/services/auth.py` → add `request_password_reset(email)` that mints a
     short-lived JWT (~1h TTL) and emails a `/reset-password?token=...` link.
   - `app/services/auth.py` → add `complete_password_reset(token, new_pwd)`.
   - `app/api/v1/auth.py` → expose `POST /v1/auth/forgot-password` (rate-limit
     by email to prevent enumeration) and `POST /v1/auth/reset-password`.
   - `backend/.env` → `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`,
     `MAIL_FROM`.

3. Frontend:
   - `pages/ForgotPassword.tsx` — email-only form, posts to /v1/auth/forgot-password.
   - `pages/ResetPassword.tsx` — reads `?token=`, asks for new password, posts.
   - Add "Need help?" link on `pages/Login.tsx` to route to `/forgot-password`.

4. E2E: extend `tests/e2e/auth.spec.ts` with the round trip — request reset,
   intercept the outbound email (or use Mailpit / Mailtrap in dev), complete
   reset, log in with the new password.

## Social login wiring (when you're ready)

Strongly recommend doing this AFTER password reset — social login looks small
but the OAuth dance + token refresh + account-linking edge cases triple the
test surface.

1. Provider — Google is the highest ROI for India. Apple is required if you
   ever ship to iOS. Facebook is dying for OTT but cheap to add.

2. Backend:
   - `pip install authlib` (or `httpx-oauth`). Add `OAUTH_GOOGLE_CLIENT_ID`,
     `OAUTH_GOOGLE_CLIENT_SECRET` env vars.
   - Add `app/api/v1/oauth.py` with `GET /v1/auth/google/start` (redirect to
     Google) and `GET /v1/auth/google/callback` (exchange code → tokens →
     find-or-create user → issue our own JWT pair).
   - Add `oauth_identity` table: `(provider, provider_user_id, user_id)`
     unique constraint so the same Google account always maps to one user.

3. Frontend:
   - "Continue with Google" button on Login + Signup that opens the start URL
     in the same tab (NOT a popup — iOS Safari blocks popups for cross-origin
     redirects).
   - After callback the backend redirects to `/auth/callback?token=...&refresh=...`
     and a small handler page stuffs them into the auth store + nav("/").

4. Account linking: when a logged-in user clicks "Connect Google" in settings
   we attach the oauth_identity to their existing record instead of creating
   a duplicate.

Budget: ~1 day of eng for Google only, ~2 days for Google + Apple together.
