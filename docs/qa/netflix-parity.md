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
| Nav | "Kids" profile mode | ❌ | Out of V1 scope — Profiles feature |
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
| Watch Trailer button (when configured) | ⚠️ | Wired but no seed title has `trailer_url` set; covered by an e2e that checks the **absence** of the button |
| Similar titles row at bottom | ❌ | No recommendation engine yet |
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
| Skip-recap overlay | ❌ | Episode model has `recap_*` fields but UI doesn't render |
| Next-episode auto-advance | ⚠️ | Cue stored, but auto-advance not implemented |
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
| Forgot password | ❌ | No password-reset email flow yet |
| Social login (Google/FB) | ❌ | Out of V1 |
| Email verification | ❌ | Out of V1 |
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
| Multiple profiles per account | ❌ | Out of V1 |

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
| HLS chunk pre-loading | ⚠️ | hls.js defaults; not tuned |

## Internationalisation

| Pattern | Status | Notes |
|---|---|---|
| UI translation (i18n) | ❌ | Out of V1 — English-only UI |
| Multi-language metadata (title / synopsis) | ⚠️ | Backend has `original_language`; no localised strings table |
| Per-region content filtering | ⚠️ | `/v1/home?country=IN` accepts param; not exposed in UI |
| Subtitle / dub language picker | ✅ | Player settings gear |

## What's strictly out of V1 (and you should know now)

These all need significant new work and most need ongoing $$:

1. **Real DRM** — Widevine/PlayReady/FairPlay license server + encryption pipeline. Without this, content is technically copyable.
2. **Profiles** — multiple Netflix-style avatars per account. Schema change + UI change + per-profile recommendations.
3. **Recommendation engine** — collaborative filtering or ML-based rec rows. Needs data + a service.
4. **Downloads for offline** — requires DRM + client-side DRM session storage.
5. **Live events / sports** — different infra entirely (low-latency HLS / LL-DASH).
6. **Native mobile apps** — current product is web-only.
7. **Password reset email** — needs SMTP / SES / Sendgrid wiring.
8. **Social login** — Google / Apple / Facebook OAuth.
9. **i18n** — translation pipeline for the UI.

If any of these are on the original client deliverable, flag them NOW so we
can scope a phase 2 contract.
