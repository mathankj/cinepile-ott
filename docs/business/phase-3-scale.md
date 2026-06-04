# CinePile — Phase 3: Scale

**Audience:** client / business partner / investors
**Period:** months 6-12+ (after Phase 1 + Phase 2 are stable and revenue-positive)
**Goal:** become a "real" OTT — native apps, real recommendations, scale infra.

When showing this deck: Phases 1 and 2 are live and **assumed working**. This is the convince-investors-to-keep-funding deck.

---

## Why this phase matters

A web-only product can launch and earn revenue. But to compete with Hotstar / Sony / Aha at any scale, **mobile apps + better infra + smarter content discovery** are non-negotiable. Phase 3 is where the product graduates from "MVP that works" to "real OTT that competes."

---

## Native applications

| App | Effort | Cost | Notes |
|---|---|---|---|
| **iOS app** | 8-12 weeks | Apple dev ₹8k/yr | React Native or Swift native. Requires DRM (FairPlay) from Phase 2. |
| **Android app** | 8-12 weeks | Play store ₹2k once | React Native shared with iOS = -30% effort. |
| **Samsung Tizen (Smart TV)** | 8 weeks | Per-store fees | Largest TV market in India. |
| **LG webOS** | 8 weeks | Free | Second largest TV market. |
| **Android TV / Google TV / Chromecast** | 6 weeks | Free | Already partially via Phase 2 Cast support. |

**Recommendation:** start with **iOS + Android via React Native** to share ~70% of code. Skip Tizen/webOS until Q4. That's 8-12 weeks for one engineer or 6-8 weeks for two.

---

## Quality + audio premium features

- **4K HDR Premium tier** (real, not just label):
  - Encode masters at 4K HEVC + HDR10. Storage cost: +5 GB/hour vs 1080p.
  - HDR10 is royalty-free; Dolby Vision needs Dolby cert (₹).
  - CDN egress costs roughly 2× per stream vs 1080p.
- **Dolby Atmos** audio:
  - Surround sound for capable devices.
  - Licensing fee per playback OR flat tier from Dolby.
- **Picture-in-picture** (we deliberately disabled it in Phase 1 as an anti-capture measure — re-enable now that DRM is doing the heavy lifting).

---

## Real recommendations

Phase 1+2 ships heuristic recommendations (same-genre seeded by reactions). Phase 3 adds:

- **ML-based recommendation engine** — collaborative filtering or content-similarity embeddings.
- **Editorial curation** layer — internal "row builder" tool for content managers.
- **Personalised home page row ordering** — different users see rows in different orders.
- **AWS Personalize** (managed) **OR** self-hosted (LightFM, implicit-feedback model).

Effort: ~2 weeks data pipeline + 2 weeks model + 1 week eval/rollout.

---

## Social features

- **User reviews / ratings** — Prime Video has this; Netflix famously doesn't.
- **Group Watch / Watch Party** — sync playback with friends. Used by Hotstar and Prime in India.
- **Activity sharing** ("I just watched X") — gentle, opt-in.

**Note:** Phase 1 + 2 deliberately omit user reviews because they can amplify toxic / spam content without moderation infrastructure. Phase 3 adds reviews **with** moderation tooling.

---

## Infrastructure for scale

- **Multi-region CDN** — currently Bunny India only. Add Bunny SE Asia / Cloudflare global.
- **Transcoding pipeline** — AWS MediaConvert or Bitmovin. Each new upload auto-transcodes to a full bitrate ladder (480p / 720p / 1080p / 4K).
- **Multi-region database** — Postgres replicas in SG + Mumbai for sub-100ms reads.
- **Backup + DR** — daily snapshots to a different cloud (cross-cloud insurance).
- **Status page** (status.cinepile.app) — public uptime + incident communication.

---

## Business model expansion

| Feature | Description | Why |
|---|---|---|
| **AVOD (free tier with ads)** | Limited library + ads | Common pattern (Hotstar / JioCinema / ZEE5). Adds top-of-funnel volume. |
| **Promo codes** | "WELCOME50" gives 50% off first month | Standard growth tool. |
| **Gift subscriptions** | Buy a plan for someone | Cultural fit for India (Diwali / Pongal gifting). |
| **Family plans** | Multi-email, shared sub | Higher ARPU than single Premium. |
| **Live events** | Concerts, religious events, weddings (NOT live sports — Hotstar moat) | Niche but high revenue per stream. |

---

## Compliance + legal

- **GDPR / DPDPA compliance** — data export, account deletion, consent log.
- **Content moderation workflow** — admin tools for takedowns + DMCA-equivalent.
- **Bug bounty / security disclosure** — formal vulnerability reporting.
- **Forensic watermark** (invisible, traceable) — Verimatrix or NAGRA, ₹15k+/mo.
- **Auto-translated subtitles** — Whisper API for SRT generation from audio.
- **Auto-dubbed audio** (AI) — ElevenLabs voice cloning per character. **Use cautiously** — current quality is OK for short clips, less good for long-form.

---

## Phase 3 budget — monthly recurring

At 10,000 paying users:

| Cost item | Monthly |
|---|---|
| B2 storage (1.5 TB) | ₹15,000 |
| CDN India + multi-region | ₹50,000-80,000 |
| Neon Postgres Scale tier | ₹8,200 |
| Contabo + load balancer + replicas | ₹2,000-5,000 |
| Razorpay 2% on ARR | ₹40,000-100,000 |
| EZDRM (from Phase 2) | ₹8,000-12,000 |
| AWS MediaConvert | ₹10,000 |
| Forensic watermarking (if enabled) | ₹15,000-30,000 |
| Sentry Team tier | ₹2,500 |
| Mailgun / Postmark | ₹3,000 |
| Intercom / Zendesk (support) | ₹15,000 |
| AI transcription / dubbing (if enabled) | ₹5,000-20,000 |
| Status page (Statuspage Pro) | ₹2,500 |
| **Total at 10k users** | **~₹176,000/mo + Razorpay %** |

At 100k paying users multiply egress + transcoding by ~10×; CDN dominates.

---

## What we DELIBERATELY skip in Phase 3

Some features look obvious but the math doesn't work:

- **Live sports / IPL** — Hotstar's moat. Rights ₹400+ crore/yr. Unwinnable.
- **Voice search** — Indian English voice recognition is rough; UX worse than typing.
- **Smart speaker integration** — Alexa / Google Home are niche for video.
- **Cloud DVR for live** — premature; no live yet.
- **Pay-per-view** — Razorpay supports it but the model isn't a fit for SVOD.

---

## Phase 3 effort summary

| Workstream | Effort |
|---|---|
| Native mobile apps (iOS + Android via RN) | 8-12 weeks |
| TV apps (Tizen + webOS + Android TV) | 16-24 weeks |
| 4K HDR + Dolby pipeline | 2-3 weeks |
| ML recommendations | 5 weeks |
| Group watch / Watch Party | 3 weeks |
| AVOD ad pipeline | 3 weeks |
| Multi-region CDN + DB | 2 weeks |
| Compliance (GDPR / DPDPA) | 1 week |
| All other rows (reviews, promo codes, family, gift, etc.) | 6-8 weeks |
| **Total** | **~6 months with 2 engineers** |

---

## When to start Phase 3

The trigger isn't a calendar date — it's a **subscriber count**.

| Subscriber count | Phase 3 readiness |
|---|---|
| < 500 paying | Stay in Phase 2. Iterate. |
| 500 - 2,000 paying | Start ML rec engine + 4K. Skip native apps. |
| 2,000 - 10,000 paying | Native apps become the bottleneck. Start them. |
| 10,000+ paying | All of Phase 3. The economics support it. |

Don't build Phase 3 in advance of demand — it bloats infrastructure cost without users to pay for it.
