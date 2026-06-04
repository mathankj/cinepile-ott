# CinePile — Master Features List

**Purpose:** Show the client every feature the platform offers, grouped by phase. Each phase later gets its own deck where future-phase features are intentionally disabled (toggled off) so the client sees a smaller, simpler product first, then watches it grow.

**How to read this:** every row is one feature. Status column tells you whether it exists in code today (✅), is partial (⚠️), or is planned (📋). The Phase column tells you which release it ships in. When showing Phase 1 to the client, hide / disable everything marked Phase 2 or Phase 3.

**Last updated:** 2026-06-04

---

## Phase 1 — Launch / V1 (months 0-3)
The minimum viable streaming product. Everything here works today; nothing additional is required from the client to ship.

| # | Feature | Area | Status | Notes |
|---|---|---|---|---|
| 1.1 | Email + password signup | Auth | ✅ | Floating-label form, RFC 6761 reserved-TLD error mapping |
| 1.2 | Email + password sign-in | Auth | ✅ | JWT access + refresh tokens, axios auto-refresh on 401 |
| 1.3 | Logout (single-device) | Auth | ✅ | Clears tokens + profile from localStorage |
| 1.4 | Profile picker ("Who's watching?") | UX | ✅ | 4 profiles per account, avatar emojis, kid flag (no enforcement yet) |
| 1.5 | Profile create / edit / delete | UX | ✅ | Modal with avatar grid, primary can't be deleted |
| 1.6 | Home page billboard (hero) | UX | ✅ | Backdrop image, Play + More Info CTAs, deterministic gradient fallback |
| 1.7 | Continue Watching row | UX | ✅ | Updates within 60s of progress event |
| 1.8 | My List row | UX | ✅ | Add/remove via card hover overlay or detail page |
| 1.9 | New Releases / Trending Now rows | Discovery | ✅ | Backend-driven (`/v1/home`) |
| 1.10 | Recommended for You row | Discovery | ✅ | Genre-similarity seeded by reactions + watchlist + history |
| 1.11 | Top in country row | Discovery | ✅ | `?country=IN` filter |
| 1.12 | Genre rows (top genres for user) | Discovery | ✅ | Auto-derived from watch history |
| 1.13 | Because You Watched X | Discovery | ✅ | Cap 2 rows, seeded by finished titles |
| 1.14 | Browse page with type + genre + sort filters | Discovery | ✅ | URL state, pagination, empty state |
| 1.15 | Search with debounce + LIKE-escape | Discovery | ✅ | 2-char minimum, special-char safe |
| 1.16 | Title detail page (movie + series) | Discovery | ✅ | Synopsis, cast, genres, episodes, age rating, runtime |
| 1.17 | Season + episode list with Play S1E1 | Discovery | ✅ | Per-season episodes, runtime, intro markers |
| 1.18 | Trailer (Watch Trailer button) | Discovery | ✅ | `trailer_url` per title |
| 1.19 | HLS video playback (Chrome/Firefox/Edge/Safari) | Player | ✅ | hls.js + native fallback |
| 1.20 | Adaptive bitrate (auto quality switch) | Player | ✅ | hls.js default ABR |
| 1.21 | Manual quality picker (Auto / 1080p / 720p / 480p) | Player | ✅ | Settings gear top-right |
| 1.22 | Multi-audio track switcher (when manifest carries them) | Player | ✅ | From hls.js audioTracks |
| 1.23 | Multi-subtitle / CC switcher | Player | ✅ | Sidecar `.vtt` + in-manifest tracks both |
| 1.24 | Skip-Intro overlay | Player | ✅ | Episode markers |
| 1.25 | Resume from last position | Player | ✅ | Per-user, per-title progress |
| 1.26 | Anti-capture cosmetic shield | Player | ✅ | Context menu block, no-download, "tab hidden = pause" curtain — NOT real DRM |
| 1.27 | Subscription: Razorpay test checkout | Billing | ✅ | Orders mode, ₹INR |
| 1.28 | Plan list page (currently 1 tier) | Billing | ⚠️ | Tier restructure pending client decision |
| 1.29 | 402 gating on paid content | Billing | ✅ | View Plans CTA appears |
| 1.30 | Cancel subscription | Billing | ✅ | Cancel-at-period-end |
| 1.31 | Reactions (thumbs up / down / double-up) | Social | ✅ | Three-state per title per user |
| 1.32 | Multi-language UI (English / Hindi / Tamil) | i18n | ✅ | Navbar globe picker, persisted to localStorage |
| 1.33 | Responsive layout (360 / 414 / 768 / 1280 / 1920) | UX | ✅ | Tablet hamburger at <1024 |
| 1.34 | Hover-reveal card overlay (Play / + / Info) | UX | ✅ | Desktop only; touch-suppressed |
| 1.35 | Keyboard accessibility on cards | UX | ✅ | Tab + focus-within ring |
| 1.36 | Admin login + dashboard | Admin | ✅ | Role: admin / content_manager / user |
| 1.37 | Admin title list + filter + search | Admin | ✅ | Includes drafts |
| 1.38 | Admin: create title (movie or series) | Admin | ✅ | Slug, year, age, language, synopsis |
| 1.39 | Admin: upload video (.mp4 to B2) | Admin | ✅ | Magic-byte sniff, 1 GB cap |
| 1.40 | Admin: upload subtitle (.vtt per language) | Admin | ✅ | Upsert per language, 5 MB cap |
| 1.41 | Admin: publish / schedule / archive | Admin | ✅ | Status workflow |
| 1.42 | Admin: soft-delete with restore | Admin | ✅ | `deleted_at` column |
| 1.43 | Admin: audit log (who did what when) | Admin | ✅ | Filterable by entity / actor |
| 1.44 | Admin: role management (admin → cm → user) | Admin | ✅ | Admin-only |
| 1.45 | Role × route access matrix (4 personas × 14 routes) | QA | ✅ | 56 access checks all passing |
| 1.46 | Backend test coverage | QA | ✅ | 144/144 passing |
| 1.47 | E2E test coverage | QA | ✅ | 108/108 desktop passing |

---

## Phase 2 — Growth (months 3-6)
Features that drive engagement and reduce churn. Each requires either eng effort (no $$) or a third-party signup (cost listed).

| # | Feature | Area | Status | Eng | $$ |
|---|---|---|---|---|---|
| 2.1 | Subscription tier ladder (Mobile / Standard / Premium) | Billing | 📋 | 1 day | None |
| 2.2 | Simultaneous stream limits per tier | Billing | 📋 | 1 day | None (Redis already on roadmap) |
| 2.3 | Device limit per tier (1 / 2 / 4) | Billing | 📋 | 1 day | None |
| 2.4 | Annual discount bump 17% → 33% | Billing | 📋 | Config change | None |
| 2.5 | Trailer auto-play on title detail (muted, 30s) | UX | 📋 | 0.5 day | None |
| 2.6 | Top 10 in India row (daily-refreshed) | Discovery | 📋 | 0.5 day | None |
| 2.7 | Manual quality cap toggle ("Use less data") | Player | 📋 | 0.5 day | None |
| 2.8 | Skip-Recap overlay (like Skip-Intro) | Player | 📋 | 0.5 day | None |
| 2.9 | Next-Episode auto-advance | Player | 📋 | 1 day | None |
| 2.10 | Watch Again row (completed titles) | Discovery | 📋 | 0.5 day | None |
| 2.11 | Profile-scoped continue-watching / watchlist / reactions | UX | 📋 | 2 days (schema change) | None |
| 2.12 | Kid mode content filter (U-rated only) | UX | 📋 | 1 day | None |
| 2.13 | Profile PIN / lock | Auth | 📋 | 1 day | None |
| 2.14 | Password reset via email | Auth | 📋 | 1 day | Mailgun free tier OK |
| 2.15 | Email verification on signup | Auth | 📋 | 0.5 day | Mailgun free tier OK |
| 2.16 | Google social login | Auth | 📋 | 1 day | Google OAuth free |
| 2.17 | Forgot password flow (UI + backend) | Auth | 📋 | 0.5 day | + 2.14 |
| 2.18 | Real DRM (Widevine + PlayReady + FairPlay) | Player | 📋 | 2 days wire-up | EZDRM ₹8-12k/mo |
| 2.19 | Downloads for offline (mobile web) | Player | 📋 | 2 days | Requires DRM (2.18) |
| 2.20 | Forensic watermark overlay (visible) | Anti-piracy | 📋 | 1 day | None |
| 2.21 | Search-result highlighting | Discovery | 📋 | 0.5 day | None |
| 2.22 | Episode list keyboard navigation | A11y | 📋 | 1 day | None |
| 2.23 | "Need help?" + help-centre stub pages | UX | 📋 | 1 day | None |
| 2.24 | Account settings page (change email, password, delete account) | Auth | 📋 | 1 day | None |
| 2.25 | "My List" page filter + sort | UX | 📋 | 0.5 day | None |
| 2.26 | Cast / Chromecast support | Player | 📋 | 1 day | None |
| 2.27 | More languages: Telugu, Kannada, Malayalam, Bengali | i18n | 📋 | 1 day per | None |
| 2.28 | A11y: WCAG 2.1 AA audit + fixes | A11y | 📋 | 3 days | None |
| 2.29 | Analytics: PostHog or self-hosted | Ops | 📋 | 0.5 day | Free tier OK |
| 2.30 | Error tracking: Sentry | Ops | 📋 | 0.5 day | Free tier OK |

---

## Phase 3 — Scale (months 6-12)
Heavy features for a real growth product. Most need 3rd-party services + meaningful eng investment.

| # | Feature | Area | Status | Eng | $$ |
|---|---|---|---|---|---|
| 3.1 | Native iOS app | Mobile | 📋 | 8-12 weeks | Apple dev ₹8k/yr |
| 3.2 | Native Android app | Mobile | 📋 | 8-12 weeks | Play store ₹2k once |
| 3.3 | TV apps (Samsung Tizen / LG webOS / Android TV) | TV | 📋 | 8-12 weeks | Per-store fees |
| 3.4 | 4K HDR Premium tier | Player | 📋 | 2 weeks | +5GB/hr storage, encoding $0.015/min |
| 3.5 | Dolby Vision / Dolby Atmos | Player | 📋 | 1 week + Dolby cert | Per-stream license |
| 3.6 | Picture-in-picture (re-enable + fullscreen toggle) | Player | 📋 | 0.5 day | None |
| 3.7 | Group watch / Watch Party | Social | 📋 | 3 weeks | None |
| 3.8 | User reviews / ratings | Social | 📋 | 1 week | None |
| 3.9 | Curated collections (editorial rows) | Discovery | 📋 | 1 week | None |
| 3.10 | Real recommendation engine (ML-based) | Discovery | 📋 | 2 weeks data + 2 weeks model | None (or AWS Personalize ₹) |
| 3.11 | Multi-region CDN (Bunny / Cloudflare) | Infra | 📋 | 1 week | ₹2-80k/mo by traffic |
| 3.12 | Transcoding pipeline (AWS MediaConvert / Bitmovin) | Infra | 📋 | 1 week | ₹2-10k/mo |
| 3.13 | Live events / live streaming | Live | 📋 | 4 weeks | Significant infra $ |
| 3.14 | AVOD (free ads-supported tier) | Billing | 📋 | 3 weeks | Ad-server fees |
| 3.15 | Promo codes / discount campaigns | Billing | 📋 | 1 week | None |
| 3.16 | Gift subscriptions | Billing | 📋 | 1 week | None |
| 3.17 | Family plan (multiple emails, shared sub) | Billing | 📋 | 2 weeks | None |
| 3.18 | Customer support tools (ticket / chat) | Ops | 📋 | 1 week | Intercom ₹15k/mo OR self-host |
| 3.19 | Status page (uptime, incidents) | Ops | 📋 | 1 day | Statuspage free tier |
| 3.20 | A/B testing (price experiments) | Ops | 📋 | 1 week | GrowthBook free self-host |
| 3.21 | GDPR / DPDPA compliance (data export, delete) | Legal | 📋 | 1 week | None |
| 3.22 | Bug bounty / security disclosure | Security | 📋 | 1 day setup | None |
| 3.23 | Forensic watermark (invisible, traceable) | Anti-piracy | 📋 | 2 weeks | Verimatrix ₹15k+/mo |
| 3.24 | Auto-translated subtitles (AI) | i18n | 📋 | 1 week | OpenAI / Whisper API ₹ |
| 3.25 | Auto-dubbed audio (AI) | i18n | 📋 | 2 weeks | ElevenLabs ₹15k+/mo |
| 3.26 | Advanced analytics dashboard for admins | Ops | 📋 | 1 week | None |
| 3.27 | Content moderation / takedown workflow | Legal | 📋 | 1 week | None |
| 3.28 | Multi-language metadata (per-title titles/synopsis) | i18n | 📋 | 1 week (schema) | None |

---

## Out of scope (explicit "we will NOT build")

These are commonly-asked but we recommend against — either Hotstar's moat, against the strategy, or just bad ROI for an India-first OTT.

| Feature | Why not |
|---|---|
| Live sports / IPL | Hotstar's moat. Rights cost ₹400+ cr/yr. Unwinnable. |
| News channels (live + DVR) | Razor-thin margins, regulatory complexity. |
| Pay-per-view (TVOD) | Razorpay supports it but the model isn't a fit for an SVOD play. |
| Cloud DVR for live | Premature; no live yet. |
| Smart speaker integration (Alexa / Google Home) | Niche for video; nice-to-have. |
| Voice search | Niche in India; English voice tech is rough on Indian accents. |
| Ringback tones / "watch like a phone call" | Not actually an OTT feature. |

---

## Phase summary

| Phase | Feature count | Eng days | Recurring $$ |
|---|---|---|---|
| **Phase 1** (launch / V1) | 47 features | 0 (already built) | ~₹3,100/mo infra |
| **Phase 2** (growth) | 30 features | ~30 days | +₹8-12k/mo if DRM (2.18) |
| **Phase 3** (scale) | 28 features | ~6 months | +₹15-150k/mo by traffic + add-ons |

---

## How to use this for the client meeting

**Phase 1 demo (the "what's working today" demo):**
- Hide / soft-disable everything in Phase 2 + 3 (set a `FEATURE_FLAG` env var or just comment out routes).
- Walk: signup → profile picker → home with all rows → browse with filters → title detail → CC + audio in player → my list → subscription.
- Tell client: "This is what we ship in Month 1. Subscriptions live, content live, customer can watch."

**Phase 2 deck (the "what we add over the next quarter" deck):**
- Each feature with a one-sentence value prop.
- Cost tags for client to greenlight (DRM is the big one).
- Show DRM, downloads, Google login, social proof features (reviews, top 10).

**Phase 3 deck (the "what makes us a real OTT" deck):**
- Native mobile apps (the biggest line item).
- 4K HDR Dolby.
- Group watch, AVOD, advanced analytics.
- This is the "convince them to keep funding" deck.

Source of truth: this file. Per-phase decks pull from these tables.
