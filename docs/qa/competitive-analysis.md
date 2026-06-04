# Indian OTT competitive analysis — Anjaneya launch positioning

Last updated: 2026-06-04. Currency: INR (₹). Researched via web sources
listed at the bottom of this doc.

Scope: pricing tiers, device + stream limits, downloads, family sharing,
ad-supported tiers, regional content, and UX patterns we may be missing.
Read alongside `netflix-parity.md` (which is the per-feature implementation
checklist).

---

## 1. Pricing tier comparison

All prices in INR per month unless noted otherwise. "—" = not offered.
"₹X/yr" indicates the only available billing cadence.

| Tier (rough equivalence) | Netflix India | Prime Video India | JioHotstar | SonyLIV | ZEE5 | Aha (Telugu) | Aha (Tamil) | Sun NXT | Anjaneya now | Anjaneya proposed |
|---|---|---|---|---|---|---|---|---|---|---|
| **Free / AVOD** | — | — | Free tier (ad-supported, limited library) | Limited free | Limited free | — | — | — | — | — (skip in V1) |
| **Mobile-only (480–720p, 1 device)** | ₹149 (480p) | — | ₹79 / ₹499/yr (720p, 1 device, ads) | ₹699/yr (720p, ads, mobile) | ₹649/yr (720p, mobile-only) | — | — | — | — | **₹99/mo or ₹799/yr** |
| **Basic (720p HD, 1 device)** | ₹199 (720p, 1 device) | — | — | — | ₹149/mo (SD, ads) | — | — | — | — | (folded into Mobile) |
| **Standard / Super (1080p, 2 devices)** | ₹499 (1080p, 2 devices) | ₹299/mo • ₹1,499/yr (HD, 3 devices, soon ad-tier) | ₹299/3mo • ₹899/yr (1080p, 2 devices, ads) | ₹399/mo • ₹1,499/yr (1080p, 2 devices) | ₹199/mo (1080p HD, 2 devices, ads) | ₹1,299/yr Telugu • ₹699/yr Tamil (1080p, ad-free) | ₹699/yr (1080p, ad-free) | ₹579/yr Basic (1080p) | **₹199/mo • ₹1,990/yr (flat, 1080p)** | **₹249/mo • ₹2,490/yr (1080p, 2 devices)** |
| **Premium (4K + HDR, 4 devices)** | ₹649 (4K HDR, 4 devices) | — (Prime caps at HD globally for India) | ₹299/mo • ₹1,499/yr → ₹2,199/yr after Jan 2026 hike (4K HDR DV, ad-free except sports, 4 devices) | ₹999/yr Premium (4K, 5 devices) | ₹1,299/yr Premium 4K (4 devices) | ₹1,499/yr Gold (4K, Dolby 5.1) | ₹1,499/yr Gold | ₹899/yr Premium (4K, 4 devices) | — | **₹499/mo • ₹4,490/yr (4K HDR when catalogue supports, 4 devices)** — *only if client funds 4K ladder* |
| **Ad-free add-on** | — (all ad-free; no ad tier yet in IN) | +₹129/mo or ₹699/yr | Bundled in Premium | Bundled in Premium | Bundled in Premium 4K | Bundled | Bundled | Bundled in Premium | n/a | n/a (all tiers ad-free at launch) |

Sources: see § 6.

**Key observations**

- The **₹149–₹199 mobile tier** is the volume driver across every Indian
  competitor. Anjaneya has no equivalent today — our cheapest entry is
  ₹199 with all features. We are leaving the price-sensitive segment
  unaddressed.
- The **typical annual discount in India is ~30–60% off the implied
  monthly rate**. JioHotstar Premium ₹299/mo × 12 = ₹3,588 vs annual
  ₹2,199 (-39%). SonyLIV ₹399 × 12 = ₹4,788 vs ₹1,499 (-69%). Anjaneya
  currently offers ₹199 × 12 = ₹2,388 vs ₹1,990 (-17%) — way under the
  Indian norm. This is leaving conversion on the table.
- **Netflix is the outlier**: highest price, ad-free only, monthly-only
  billing in India. Their bet is brand + originals. We cannot win that
  bet, so we should price closer to Hotstar/Sony.
- **Aha is the closest comp** in size, content philosophy, and audience
  (regional South India, ad-free yearly plans). Their entry point is
  ₹699/yr Tamil-only. That is the lower bound we should think about for
  a future "regional only" SKU.

---

## 2. Device + simultaneous stream limits

| Plan tier | Netflix IN | Prime Video IN | JioHotstar | SonyLIV | ZEE5 | Aha | Anjaneya now | Anjaneya proposed |
|---|---|---|---|---|---|---|---|---|
| Mobile | 1 device, mobile/tablet only | n/a | 1 device, mobile only | 1 device | 1 device | n/a | n/a | **1 device, mobile/tablet only** |
| Basic | 1 device, all surfaces | n/a | n/a | n/a | 1 device | n/a | unlimited (no enforcement) | (folded into Mobile) |
| Standard / Super | 2 simultaneous, ~download on 2 | 3 simultaneous | 2 simultaneous | 2 simultaneous | 2 simultaneous | 2 simultaneous | unlimited (no enforcement) | **2 simultaneous, downloads on 2** |
| Premium | 4 simultaneous, downloads on 6 | n/a (capped at 3) | 4 simultaneous | 5 simultaneous | 4 simultaneous | 4 simultaneous | n/a | **4 simultaneous, downloads on 4** |

**Gap:** Anjaneya does not enforce simultaneous-stream limits at all.
This is a real risk — one paying account can be shared across an entire
extended family. Worth adding before paid launch: a simple Redis-keyed
"active sessions per user" check on `/api/playback/start`, kick the
oldest session on 4th concurrent play.

---

## 3. Feature comparison matrix

Legend: ✅ supported · ⚠️ partial / paywalled · ❌ not offered · 🆕 added recently

| Feature | Netflix IN | Prime IN | JioHotstar | SonyLIV | ZEE5 | Aha | Anjaneya now |
|---|---|---|---|---|---|---|---|
| **Pricing & business** | | | | | | | |
| Mobile-only sub | ✅ | ❌ | ✅ | ✅ | ✅ | ❌ | ❌ |
| Free / AVOD tier | ❌ (IN) | ❌ | ✅ | ⚠️ | ⚠️ | ❌ | ❌ |
| Annual plan | ❌ (monthly only IN) | ✅ ₹1,499/yr | ✅ | ✅ | ✅ | ✅ | ✅ (₹1,990) |
| Quarterly plan | ❌ | ✅ ₹599 | ✅ | ✅ | ✅ | ✅ | ❌ |
| Ad-supported price tier | ❌ (IN) | ✅ add-on | ✅ | ⚠️ | ✅ | ❌ | ❌ |
| Family / shared profiles (5+) | ✅ 5 | ✅ 6 | ✅ 4 | ✅ 4 | ✅ 4 | ✅ 4 | ✅ (no hard cap) |
| Kids profile mode | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| Simultaneous-stream enforcement | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| **Content** | | | | | | | |
| Hindi originals | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | depends on catalogue |
| Tamil / Telugu / regional | ✅ (ramping) | ✅ | ✅ | ✅ | ✅ | ✅ (core) | depends on catalogue |
| Live sports (IPL etc) | ❌ | ❌ (some) | ✅ (IPL, ICC, football — USP) | ✅ (WWE, FIFA) | ✅ (some) | ❌ | ❌ |
| Live TV channels | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ |
| 4K HDR catalogue | ✅ | ⚠️ | ✅ | ✅ | ✅ | ✅ | ❌ |
| Dolby Vision / Atmos | ✅ | ⚠️ | ✅ | ⚠️ | ❌ | ⚠️ | ❌ |
| **Playback UX** | | | | | | | |
| HLS adaptive bitrate | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Manual quality cap (cellular) | ✅ "Use less data" | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| Trailer auto-play on detail page | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ⚠️ | ❌ |
| Hover-preview on tile (web) | ✅ | ⚠️ | ⚠️ | ❌ | ❌ | ❌ | ❌ |
| Skip Intro (auto-detected) | ✅ ML-detected | ✅ (manual) | ✅ | ✅ | ⚠️ | ⚠️ | ⚠️ stub |
| Skip Recap | ✅ | ✅ | ⚠️ | ❌ | ❌ | ❌ | ❌ |
| Next-episode auto-advance | ✅ ~10 s | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ |
| Picture-in-Picture | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ❌ (intentionally disabled) |
| Chromecast | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| AirPlay | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ⚠️ | ❌ |
| Continue Watching | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Watchlist / My List | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Top 10 in India row | ✅ (USP) | ❌ | ⚠️ trending | ⚠️ | ⚠️ | ⚠️ | ❌ |
| Multi-language subtitles | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Multi-language audio tracks | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| **Discovery** | | | | | | | |
| Personalised home rows | ✅ best-in-class | ✅ | ✅ | ⚠️ | ⚠️ | ⚠️ | ⚠️ basic |
| User reviews / ratings | ❌ | ✅ X-Ray (no IMDb scores in player though) | ❌ | ❌ | ❌ | ❌ | ✅ reactions |
| IMDb integration | ❌ | ✅ X-Ray cast/trivia | ❌ | ❌ | ❌ | ❌ | ❌ |
| Search by genre/language/year | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Offline & social** | | | | | | | |
| Downloads for offline (mobile) | ✅ (limits vary) | ✅ | ✅ Super/Premium | ✅ | ✅ Premium | ✅ | ❌ |
| GroupWatch / Watch Party | ❌ | ✅ ("Watch Party", web only, beta) | ✅ ("Watch'N Play" during IPL) | ❌ | ❌ | ❌ | ❌ |
| Native mobile apps | ✅ iOS/Android/TV | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ (web only) |
| Smart TV apps | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| **Auth & security** | | | | | | | |
| Social login (Google/Apple) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| Password reset (email/OTP) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| OTP / phone login | ⚠️ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| Real DRM (Widevine L1 / FairPlay) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| Forensic watermarking | ✅ (sports/4K) | ✅ | ✅ (IPL) | ⚠️ | ❌ | ❌ | ❌ |

---

## 4. India-specific learnings

These are the structural realities of the Indian OTT market that should
shape Anjaneya's launch.

**ARPU is brutally low.** Statista projects India OTT ARPU at ~US$9/yr
(~₹750/yr) for 2026. Blended SVOD ARPU sits around ₹125–200/mo, AVOD
ARPU is closer to ₹12–20/mo. That is roughly **1/10th of the US**. The
implication: do not over-engineer for the per-subscriber unit economics
of a US OTT. Every ₹ of monthly infra/license cost matters.

**Annual plans dominate revenue.** Indian users overwhelmingly buy
annual subs (cheaper effective price + telco bundle reach). Most
competitors price annual at **30–60% off implied monthly**. Anjaneya's
current 17% annual discount is undersized — bumping it to 30–40% will
likely shift the mix and lower churn.

**Telco bundling is how most OTT subs are acquired.** Jio and Airtel
recharge packs bundle JioHotstar, Netflix Mobile, Prime, SonyLIV, etc.
A standalone OTT in India that doesn't have a telco partnership is
fighting uphill on CAC. Worth a strategic conversation with the client
about Jio/Airtel partnership timelines.

**Sports = the moat.** JioHotstar's IPL exclusivity is the single
biggest reason it dominates (~750M viewers claimed). We will not
out-spend them on cricket rights. Don't try. Pick a focused content
identity instead (regional originals, devotional, classics — whatever
Anjaneya's catalogue actually leans into).

**Regional content is the second moat.** Aha (Telugu/Tamil) and Sun NXT
(South 4 languages) survive purely on language-specific catalogues at
₹699–₹1,499/yr. That model works because regional audiences are
under-served by Netflix/Prime and willing to pay specifically for their
language. If Anjaneya's catalogue is regionally weighted, a
**language-specific annual SKU at ₹699–₹999** is the highest-leverage
pricing experiment.

**Free / ad-supported is now the norm.** JioCinema (now JioHotstar) free
tier, MX Player + miniTV (250M MAU), ZEE5 free, SonyLIV free section —
the Indian consumer expects a free entry surface. Netflix is the only
holdout. For Anjaneya, an **ad-light free preview tier** (e.g., 1
movie/month free with a 30-sec ad) is worth scoping for V2; it doubles
as marketing.

**Multi-language subtitles + dub is table stakes.** Every competitor
ships Hindi + Tamil + Telugu + Malayalam + Bengali + Marathi audio /
subs. We have multi-lang subtitles ✅ but not multi-audio tracks. Worth
adding.

**Family of 4–5 is the unit, not the individual.** Indian households
share OTT subs aggressively. The 4-profile + 4-device + downloads-on-4
combo is the family Premium expectation. We do not have device
enforcement at all — easy to add and protects revenue at scale.

---

## 5. Recommendations for Anjaneya

### 5.1 Pricing tier proposal — 3 tiers

Replace the current flat ₹199/mo + ₹1,990/yr with a Mobile / Standard /
Premium ladder, mirroring what every Indian competitor does. Price
points calibrated to undercut JioHotstar Premium and match SonyLIV
Standard, while still beating Aha annual on the entry tier.

| Tier | Monthly | Annual | Annual discount | Resolution | Devices | Simul streams | Downloads |
|---|---|---|---|---|---|---|---|
| **Mobile** | ₹99 | ₹799 | 33% off | 720p | Mobile/tablet only | 1 | 5 |
| **Standard** | ₹249 | ₹1,990 | 33% off | 1080p | All surfaces | 2 | 10 per device, 2 devices |
| **Premium** | ₹499 | ₹3,990 | 33% off | 4K HDR* | All surfaces | 4 | 25 per device, 4 devices |

*Premium 4K only ships if the client signs off on the encoding-cost
delta (see § 5.3). Until then, Premium = 1080p + ad-free + 4 devices,
priced at ₹399 / ₹3,190.

**Why these numbers**

- ₹99 mobile beats JioHotstar's ₹79 mobile on features (HD vs SD)
  while still feeling cheap.
- ₹249 standard matches the SonyLIV / Netflix Basic price band where
  the volume of Indian SVOD revenue actually sits.
- ₹499 premium is the same as SonyLIV monthly Premium and below
  Netflix Premium ₹649 — credible 4K positioning without overshooting.
- 33% annual discount lands in the middle of the competitor range
  (Hotstar -39%, SonyLIV -69%) — generous enough to move the mix
  toward annual without giving away margin.

### 5.2 Device / quality tier mapping (technical)

Encoding ladder per tier. Costs flagged are *additional B2 storage +
encoding compute* vs current ladder.

| Rendition | Mobile | Standard | Premium | Encoding cost vs current |
|---|---|---|---|---|
| 240p @ 400 kbps | ✅ | ✅ | ✅ | already shipped |
| 480p @ 800 kbps | ✅ | ✅ | ✅ | already shipped |
| 720p @ 2 Mbps | ✅ cap | ✅ | ✅ | already shipped |
| 1080p @ 5 Mbps | ❌ | ✅ cap | ✅ | already shipped |
| 1440p @ 10 Mbps | ❌ | ❌ | ✅ | +~15% storage, +~10% encode |
| 4K @ 15 Mbps HEVC | ❌ | ❌ | ✅ | **+~60% storage, ~2× encode time, needs HEVC license** |
| Dolby Vision | ❌ | ❌ | ✅ | encoder license ~$10–25K/yr typical |
| Dolby Atmos | ❌ | ❌ | ✅ | per-title encoding fee, audio bitrate +500 kbps |

Enforcement: a single field on `Subscription` (`max_resolution`,
`max_devices`, `max_concurrent_streams`) gated in the
`/api/playback/manifest` endpoint. Server picks the variant cap, ABR
picks within it. Roughly half a day of backend work.

### 5.3 Cost-effective feature priorities — high impact, low cost

These are the gaps from § 3 that move the launch needle most for least
effort. Rough effort = engineering days.

| Feature | Impact | Effort | Notes |
|---|---|---|---|
| Simultaneous-stream limit | High (revenue protection) | 1 d | Redis active-session set per user. |
| Password reset via email | High (table stakes; current blocker for paid users) | 2 d | SES/SMTP + token table + 2 routes. |
| Social login (Google) | High (signup conversion +20–40% typical) | 2 d | Authlib already in stack; just wire it. |
| Annual discount bump to 33% | High | 0.5 d | Price config change + checkout copy. |
| Trailer auto-play on detail page | Medium-High (Netflix's most copied pattern) | 1 d | We already have HLS player; reuse muted+looped. |
| Multi-audio track support | Medium (regional dub) | 2 d | HLS spec already supports; admin upload UI + manifest changes. |
| Manual quality cap toggle | Medium (data-saving is a real concern in IN) | 1 d | Profile setting + hls.js `maxAutoLevel`. |
| Top 10 in India row | Medium (Netflix's USP, simple to clone) | 1 d | SQL aggregate over last 7 days `play_starts`. |
| Skip Intro / Recap proper UX | Medium | 1 d | Admin sets intro_start/intro_end per episode; button appears in player. |
| Forensic watermark (visible) | Low-Medium (deterrent for casual piracy) | 2 d | Burn email/user-id overlay into player; not real forensic but cheap. |
| Chromecast support | Medium (TV is where families watch) | 3 d | Cast Sender SDK in web player. |

**Total ~16 days** for the full high-impact backlog. Pick the top 5 (8
days) and the launch story is meaningfully stronger.

### 5.4 Strategic features that need a client decision

These are too expensive or too philosophical for engineering to decide
unilaterally. Bring to the client.

- **Real DRM (Widevine L1 + FairPlay + PlayReady).** Multi-DRM service
  costs $500–2,500/mo at our scale. Without it, no major studio will
  license premium content. Decision: only required if catalogue
  includes licensed Hollywood / studio content. If Anjaneya is
  originals + library only, can defer to V2.
- **Downloads for offline.** Requires either (a) DRM + persistent
  license server, or (b) progressive download with watermark and time
  bomb. The (a) path is the right one but couples to the DRM decision
  above. ~2 weeks of work once DRM is in.
- **Native mobile apps (iOS + Android).** ~8–12 weeks for the pair, or
  Capacitor/React Native wrap of existing web in 3 weeks at the cost of
  download/PiP/Chromecast feeling janky. Decide path before committing.
- **Live TV / live events.** Requires an entirely separate ingest +
  CDN + DVR stack. Hotstar's USP — not worth chasing unless Anjaneya
  has a specific live-rights deal (e.g., devotional channels, regional
  news).
- **Ad-supported free tier.** Needs ad server (Google Ad Manager / SpotX
  / Magnite). 4–6 weeks. The payoff is funnel volume and AVOD revenue.
  Probably V2 unless growth is the explicit launch KPI.
- **4K HDR + Dolby Vision/Atmos.** Encoder licenses + per-title fees.
  Only worth it if Premium tier is funded and catalogue has masters in
  the required format. Defer until we know the catalogue.
- **Telco partnership (Jio/Airtel bundle).** Not an engineering
  decision but the single biggest distribution lever in India. Client
  conversation, not a code change.

---

## 6. Sources

Pricing sourced June 2026 — Indian OTT prices change every ~6 months,
re-verify before any pricing decision is finalised.

- Netflix India plans: https://help.netflix.com/en/node/24926 ·
  https://www.digit.in/digit-binge/ott/netflix/ ·
  https://dealsdekho.co.in/blog/netflix-subscription-plans
- Netflix download limits: https://streamfab.dvdfab.cn/blog/netflix-download-limit.htm ·
  https://help.netflix.com/en/node/64923
- Netflix India ad-free hold-out: https://www.whalesbook.com/news/English/media-and-entertainment/Netflix-India-Ad-Free-Plan-Faces-Growing-Market-Pressure/69e86c2cbca97ee1069ebc60
- Netflix recommendations / Top 10: https://help.netflix.com/en/node/100639 ·
  https://top10.netflix.com/india.html
- Netflix Skip Intro ML: https://dev.to/abhivyaktii/the-magic-behind-netflixs-skip-intro-feature-1p1o
- Prime Video India plans: https://www.amazon.in/gp/help/customer/display.html?nodeId=G34EUPKVMYFW8N2U ·
  https://www.aboutamazon.in/news/retail/new-amazon-prime-membership-plans-in-india ·
  https://www.digit.in/digit-binge/ott/prime-video/
- Prime Video Watch Party IN: https://www.thenewsminute.com/atom/amazon-prime-video-launches-social-viewing-feature-watch-party-india-139204
- Prime X-Ray: https://www.amazon.com/salp/xray · https://psyduct.com/amazon-prime-videos-x-ray-feature-69fe7c1274c4
- JioHotstar plans 2026: https://telecomtalk.info/jiohotstar-subscription-plans-2026-mobile-super-premium/1004394/ ·
  https://www.cashify.in/jiohotstar-subscription-plans-pricing-monthly-annually-and-features ·
  https://www.smartprix.com/bytes/jiohotstar-prices-hiked-for-2026-new-monthly-plans-introduced-as-premium-annual-rates-jump-47/
- JioHotstar device limits: https://technosports.co.in/hotstar-device-login-limit-complete-guide/
- JioHotstar IPL features: https://www.newsx.com/entertainment/jio-hotstar-ipl-2026-live-streaming-how-to-watch-latest-match-online-subscription-plans-tv-telecast-more-226053/
- SonyLIV plans: https://www.sonyliv.com/subscription · https://www.cashify.in/sony-liv-subscription-plans-explained-monthy-yearly-plans
- JioCinema legacy pricing: https://techcrunch.com/2024/04/24/jiocinema-launches-35-cent-premium-tier-stepping-up-rivalry-with-netflix-and-prime-video/ ·
  https://www.subsplit.in/blog/jiocinema-premium-plans-india
- ZEE5 plans: https://www.zee5.com/global/myaccount/subscription ·
  https://helpcenter.zee5.com/portal/en/kb/articles/4k-subscription-plan-rs-1499 ·
  https://www.digit.in/digit-binge/ott/zee5/
- Aha plans: https://www.aha.video/subscription/viewplans · https://www.filmibeat.com/aha-video-subscription-price-plans-3
- Sun NXT plans: https://www.filmibeat.com/sun-nxt-subscription-price-plans-25 ·
  https://couponswala.com/blog/sun-nxt-plans/
- MX Player + miniTV: https://www.aboutamazon.in/news/entertainment/amazon-minitv-mx-player-merger ·
  https://variety.com/2026/tv/news/amazon-mx-player-merges-prime-video-india-1236740262/
- India OTT market size + ARPU: https://www.statista.com/outlook/amo/media/tv-video/ott-video/india ·
  https://www.apprupt.com/india-svod-market-statistics ·
  https://www.apprupt.com/india-ott-market-forecasts-statistics
- Netflix regional content strategy IN: http://about.netflix.com/en/news/next-on-netflix-india-2026 ·
  https://www.whats-on-netflix.com/coming-soon/netflix-india-announces-new-tamil-telugu-originals-for-release-in-2026/
- DRM + forensic watermarking pricing: https://go.buydrm.com/thedrmblog/forensic-watermarking-drm-the-dynamic-duo-for-bulletproof-content-security-in-2026 ·
  https://onewrk.com/how-much-does-digital-rights-management-cost/ ·
  https://www.vdocipher.com/blog/forensic-watermarking/
