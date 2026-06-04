# CinePile — Phase 2: Growth

**Audience:** client / business partner
**Period:** months 3-6 (launch + 90 days)
**Goal:** retain Phase 1 subscribers and unlock the next price tier

When showing this deck, everything in Phase 1 is **assumed running**. Phase 3 features stay hidden.

---

## Why this phase matters

Phase 1 proves the product works. Phase 2 proves the **business model** works. The features here drive higher ARPU (the tier ladder + 4K), reduce churn (DRM-protected content partnerships become possible), and lower acquisition friction (Google login, password reset).

---

## The features

### Pricing ladder (3 tiers instead of 1)

| Tier | Price/mo | Price/yr | Quality | Devices | Simultaneous |
|---|---|---|---|---|---|
| **Mobile** | ₹99 | ₹799 | 720p (mobile + tablet only) | 1 | 1 |
| **Standard** | ₹249 | ₹2,490 | 1080p HD (all devices) | 2 | 2 |
| **Premium** | ₹499 | ₹4,490 | 4K HDR + Dolby (where available) | 4 | 4 |

Replaces the flat ₹199/mo from Phase 1. Annual discount jumps from 17% → 33% (Indian market norm).

### DRM + Downloads
- **Real DRM** — Widevine (Chrome/Android), PlayReady (Edge/Windows), FairPlay (Safari/iOS) via EZDRM license server.
- **Downloads for offline** on Mobile + Standard + Premium tiers. Mobile = 1 download slot, Standard = 2, Premium = 4.
- **Cost:** EZDRM ~₹8,000-12,000/month minimum + per-license fees.

### Auth upgrades
- **Google social login** ("Continue with Google" button).
- **Password reset via email** with Mailgun (free tier).
- **Email verification** on signup.
- **Forgot password / "Need help?"** real working flow.

### Player polish
- **Trailer auto-play** on title detail (muted, 30 sec) — Netflix-iconic.
- **Skip-Recap** overlay (like Skip Intro).
- **Next-Episode auto-advance** with countdown.
- **Manual quality cap** toggle: "Use less data" → forces 480p.
- **Chromecast / Google Cast** support.

### Discovery upgrades
- **Top 10 in India** row (daily-refreshed).
- **Watch Again** row for completed titles.
- **Search-result highlighting** of matched terms.
- **Editorial collections** (curator-picked rows).

### Profile system upgrades
- **Profile-scoped continue-watching, watchlist, reactions** — each profile has its own history.
- **Kid mode content filter** — U-rated titles only when kid profile is active.
- **Profile PIN / lock** — keep kids out of adult profiles.

### Accessibility & A11y
- **WCAG 2.1 AA audit + fixes** — 3 eng days; required for some enterprise / accessibility-mandated markets.
- **Episode-list keyboard navigation** — full arrow-key + roving tabindex.
- **More languages**: Telugu, Kannada, Malayalam, Bengali (1 day per).

### Operations
- **Sentry** error tracking.
- **PostHog** product analytics (or self-hosted).
- **Account settings** page (change email, change password, delete account — DPDPA-compliant).

### Anti-piracy lite
- **Visible forensic watermark** overlay — user ID + timestamp in a corner during playback. Cosmetic but deterrent.

---

## Phase 2 effort

- **Total eng:** ~30 days (1 dev for ~6 weeks, or 2 devs for 3 weeks).
- **Critical-path items** (do these first):
  1. Pricing tier restructure (1 day)
  2. Simultaneous-stream enforcement (1 day)
  3. DRM provider integration + content re-encoding (1 week)
  4. Password reset + Google OAuth (2 days)
  5. Trailer auto-play + Skip-Recap + Next-Episode (2 days)

The other Phase 2 features can roll out as smaller incremental releases.

---

## Phase 2 budget — monthly recurring

| Cost item | Additional cost over Phase 1 |
|---|---|
| EZDRM (license server) | +₹8,000-12,000/mo |
| Mailgun (above free tier) | +₹500-3,000/mo at scale |
| PostHog (if cloud) | +₹0-4,000/mo |
| Sentry (above free tier) | +₹0-2,500/mo |
| Sub-total Phase 2 add-ons | **~₹8,500-21,500/mo** |
| Carry-over from Phase 1 | ₹3,025/mo |
| **Phase 2 total** | **~₹11,500-24,500/mo + Razorpay 2%** |

### Break-even at Phase 2 (with new tier ladder)
- ~120 Standard subscribers — OR —
- ~60 Premium subscribers
covers Phase 2 infra cost.

---

## What's intentionally still hidden in Phase 2

Phase 3 features stay off:
- ❌ Native mobile / TV apps (web-only still)
- ❌ Group watch / Watch Party
- ❌ User reviews / ratings
- ❌ ML recommendation engine
- ❌ Multi-region CDN scale-out
- ❌ Live events / live streaming
- ❌ AVOD (free tier with ads)
- ❌ Family plan (multi-email)

---

## What we need from client to start Phase 2

1. **Pricing approval** for 3-tier ladder (or counter-proposal).
2. **EZDRM contract signature** (~3 days for KYC + bucket whitelist).
3. **Mailgun account** (free tier registration — 10 min).
4. **Google Cloud OAuth credentials** — ~30 min.
5. **(Optional) decision on forensic watermark provider** — Verimatrix takes longer to onboard than EZDRM.

Once those are in: Phase 2 ships **in 6 weeks** from kickoff.
