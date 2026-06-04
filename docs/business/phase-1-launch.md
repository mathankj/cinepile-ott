# CinePile — Phase 1: Launch

**Audience:** client / business partner / investors
**Period:** months 0-3 from contract signing
**Deliverable status:** all features below are LIVE and tested in code today

When showing this deck: everything in Phase 2 and Phase 3 is **intentionally disabled** in the demo build. The client sees a focused, working product, not vapourware.

---

## What launches in Phase 1

### Customer experience
- **Sign-up / sign-in** with email + password. Floating-label form, branded.
- **"Who's watching?" profile picker** — up to 4 profiles per account, custom avatars, kids flag.
- **Home page** with cinematic billboard hero, multi-row catalog: Continue Watching, My List, New Releases, Trending Now, Recommended for You, Top in India, genre rows, Because You Watched.
- **Browse + filter + sort** by movie / series / genre / newest / most-watched.
- **Search** with debounce + multi-language support.
- **Title detail** pages with synopsis, cast, episodes, trailer.
- **Three-state reactions**: thumbs up, double-thumbs (love), thumbs down.
- **My List** add/remove via card hover.
- **Multi-language UI**: English, Hindi, Tamil out of the box. Globe icon to switch.
- **Responsive** layout: mobile / tablet / laptop / desktop — every page tested at 5 viewports.

### Playback
- **HLS streaming** with adaptive bitrate (auto quality).
- **Manual quality picker** in a Netflix-style settings gear.
- **Multi-audio track switcher** when manifest carries multiple languages.
- **Closed Captions / Subtitles** — admin uploads `.vtt` per language; player auto-attaches.
- **Skip Intro** overlay on episodes.
- **Resume from last position** per user.
- **Anti-capture shield** (cosmetic): right-click block, no-download, "tab hidden = pause."

### Billing
- **Single subscription tier** at ₹199/mo or ₹1,990/yr (will restructure in Phase 2; see notes).
- **Razorpay checkout** in test mode for QA; flip to production mode at launch.
- **402 paywall** with View Plans CTA on paid content.
- **Cancel anytime** at period end.

### Admin
- **Title creation** form (movies + series).
- **Video upload** to Backblaze B2 (1 GB max, magic-byte validation).
- **Subtitle upload** per language (`.vtt` sidecar, 5 MB max).
- **Publish / schedule / archive** workflow.
- **Audit log** — every change attributed to an admin user.
- **Role management**: admin → content_manager → user.

### Quality bar
- **Backend tests**: 144/144 passing.
- **End-to-end tests**: 108/108 desktop passing.
- **Role × route access matrix**: 56 access checks all passing (anonymous, regular user, content_manager, admin × every route).

---

## What is INTENTIONALLY hidden from the client in Phase 1

(These exist in the codebase but are toggled off until Phase 2.)

- ❌ DRM / Widevine / FairPlay → "anti-capture" is shown instead (cosmetic only — explained honestly).
- ❌ Downloads for offline → not on the Phase 1 menu.
- ❌ Google / Apple / Facebook social login → email + password only.
- ❌ Password reset via email → "Contact support" stub for now.
- ❌ Subscription tier ladder → single flat tier.
- ❌ Simultaneous-stream limits → not enforced (no Premium tier yet).
- ❌ Kid-content filter → toggle exists, no enforcement yet.
- ❌ Profile-scoped history → shared across all profiles per account.

The conversation in the demo: "we have all of these designed and partially-built. Phase 2 turns them on, one quarter from now, after we see launch metrics."

---

## Phase 1 budget — monthly recurring

| Cost item | At launch (low traffic) | Notes |
|---|---|---|
| Backblaze B2 storage | ₹500 | ~50 GB; grows linearly with catalog size |
| CDN (Bunny India) | ₹2,000 | ~100 GB/mo egress |
| Neon Postgres | ₹0 | Free tier good for V1 |
| Contabo VPS | ₹400 | Backend + frontend |
| Razorpay | 2% per txn | No flat fee |
| Domain + SSL | ₹125 | anjaneya.app or cinepile.app |
| Sentry, Mailgun, monitoring | ₹0 | Free tiers OK |
| **Total** | **~₹3,025/mo** | Plus 2% of revenue |

### Break-even
- 30 paying Mobile subscribers (Phase 2 tier) — OR —
- ~12 Standard subscribers — OR —
- ~6 Premium subscribers
covers Phase 1 infra cost.

---

## Phase 1 deliverables checklist

- [x] Backend API (FastAPI + Postgres + B2 storage)
- [x] Web frontend (React + Vite + Tailwind v4)
- [x] Admin panel
- [x] HLS video player with quality / audio / subtitle switcher
- [x] Subscription + Razorpay test checkout
- [x] Multi-language UI (EN / HI / TA)
- [x] Profile system
- [x] Responsive design
- [x] 252 automated tests
- [x] Comprehensive QA audit + final report
- [x] DRM scaffolding (off; ready for Phase 2 plug-in)
- [x] Internationalisation infrastructure (i18next)
- [x] Subtitle sidecar upload pipeline
- [x] GitHub repo (private)

---

## What we need from client to launch

1. **Domain choice** (cinepile.app vs cinepile.in vs something else). 1 day to register.
2. **Final pricing tier**:
   - Option A (safe): single ₹199/mo for V1; tier ladder in Phase 2.
   - Option B (recommended): launch with Mobile ₹99 + Standard ₹249 from day 1.
3. **Razorpay production keys** (KYC + bank-account verification — 3-5 days).
4. **Production storage credentials** (Backblaze B2 production bucket — 30 min).
5. **Brand assets**: hero background image, favicon, light-mode logo if needed.
6. **Content uploads**: client provides 10-20 launch titles (we have placeholders for demo).

When all 6 are in our hands, **launch in 2 weeks**.
