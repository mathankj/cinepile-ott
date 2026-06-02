# Netflix Admin / CMS — Research

**Date:** 2026-06-02
**Purpose:** Source material for ADR-0002 admin-side decisions.

---

## 1. Netflix's actual admin platforms

**Netflix Studio / Media Production Suite** — umbrella set of cloud-native tools for productions, vendors, internal teams. Components publicly named: **Content Hub** (asset storage/management/collab/delivery), **Footage Ingest** (uploads OCF — Original Camera Files — directly to cloud), **Media Library** (search/preview/share/download), **Dailies** (automated QC, sound sync, color), **Remote Workstations** (cloud editorial), **VFX Pulls / Conform Pulls** (automated plate + OCF delivery to vendors), **Media Downloader**. Onboarding stack: **Starship** (access mgmt), **Asset QC**, OCF Import.

**Backlot** — Netflix's partner portal for **fulfillment**: streaming deliverables (IMF video, Dolby Atmos ADM BWAV audio, timed text). ~10 years old, ~2.5M requests/year. Models work as **Source Requests**, **Deliveries**, **QC Requests**. Public API at `backlot-api-docs.prod.netflixstudios.com`.

**Licensed-content workflow**: (1) licensing deal closed (Avails); (2) Netflix grants Backlot access; (3) Source Request lists required deliverables — IMF master, per-language audio, per-language subs/SDH, artwork, metadata; (4) packaged in **IMF** (SMPTE ST 2067-21); (5) **IaaS** automated checks; (6) Manual QC by Netflix QC Ops or partners; (7) failures → redelivery; (8) on pass, transcoded, gated by Title Launch Date. First-submission rejection rate: 20–30%.

## 2. Content lifecycle states

| State | Definition | User-visible? |
|---|---|---|
| `planned` / `greenlit` | Title approved, no production yet | No |
| `in_production` | Principal photography | No |
| `in_post` | Editorial, sound, VFX, color | No |
| `delivered` | Master + assets uploaded (IMF + audio + subs) | No |
| `inspection` (IaaS) | Automated structural/spec checks | No |
| `qc_pending` / `qc_failed` / `qc_passed` | Manual QC outcome | No |
| `redelivery` | Vendor must resubmit | No |
| `encoded` | Transcoded to streaming ladders | No |
| `scheduled` | Awaiting Title Launch Date | No (trailer/PDP may be visible) |
| `live` | Playable in licensed territories | Yes |
| `expiring_soon` | Within license-end window | Yes |
| `removed` / `delicensed` | Pulled at license expiry | No (still in DB; downloads invalidate) |
| `archived` | Cold storage per lifecycle policy | No |

**Scheduled publish**: per-title `title_launch_date` (TLD) UTC; Netflix Originals release at 00:00 Pacific globally, licensed titles at 00:00 local time per region. Implemented as per-region availability windows `(region, start_at, end_at)`, NOT a single `publish` boolean.

## 3. Asset model

**Per-title asset bundle** (modeled around IMF + supplementals):

- **Mezzanine / Master video** — IMF Composition Playlist (CPL) referencing video Track Files (JPEG2000 / ProRes 422 HQ, 4K UHD HDR10 + Dolby Vision)
- **Encoded variants** — per-codec ABR ladders (H.264, HEVC, AV1) × resolutions × bitrates
- **Audio tracks** — per language; original + dubs; Dolby Atmos ADM BWAV, 5.1, 2.0; ~36 languages
- **Subtitle tracks** — per language; format **TTML1** globally, **IMSC 1.1** for Japanese
- **SDH / CC tracks** — per language
- **Dub cards / forced narratives** — per locale
- **Artwork** — title-art (boxshot), background, logo overlays, **per-locale localized title treatments**, multiple aspect ratios; grouped by `lineage_id` (shared background image across variants for cross-locale A/B aggregation)
- **A/B variants** — multi-armed bandit; 5–7 variants per title
- **Trailers / teasers / BTS / clips** — first-class assets with their own identifiers
- **Metadata bundle** — title, synopsis (per locale), runtime, genre, cast/crew, ratings, content advisories (MEC-compliant)

**Per-asset metadata to model**: `asset_id`, `parent_title_id`, `eidr_id`, `asset_type` enum, `codec`, `bitrate`, `resolution`, `hdr_profile`, `language` (BCP-47), `region_availability[]`, `aspect_ratio`, `locale`, `version`, `supersedes_asset_id`, `checksum`, `byte_size`, `created_by`, `created_at`, `qc_status`, `qc_report_id`, `effective_from`, `effective_until`, `lineage_id`.

**Versioning**: IMF designed for "version-itis" — single master + **Supplemental Compositions** (alt edits, censored cuts, regional language burn-ins) referencing master via CPL. Updated artwork supersedes but old retained (`supersedes_asset_id`, `is_current` flag).

## 4. Series / season / episode admin operations

- Hierarchy: Series → Season → Episode. Limited Series modeled as Series with one season + `series_type ∈ {ongoing, limited, mini, anthology}`. Anthology seasons can have independent casts.
- Per-episode upload is the norm — IMF/Backlot deliveries are per asset; weekly-release shows ingest episode-by-episode. Whole-season batches still N independent IMF deliveries gated by one TLD.
- Reordering: episodes carry an `ordinal` integer; rare in practice but happens for re-cuts. Mutable integer column, not derived from `created_at`.
- Episode states are independent — one episode can be `live` while another is `qc_pending` (matters for weekly releases).

## 5. Roles + permissions matrix

| Role | Read | Upload | Trigger QC | Approve QC | Edit meta | Schedule | Publish | Pull | User mgmt |
|---|---|---|---|---|---|---|---|---|---|
| `viewer` | Y | – | – | – | – | – | – | – | – |
| `production_partner` | own | Y | – | – | – | – | – | – | – |
| `fulfillment_partner` | assigned | Y | auto | – | – | – | – | – | – |
| `catalog_editor` | Y | – | – | – | Y (draft) | – | – | – | – |
| `localization_manager` | Y | subs/dubs | Y | – | locale | – | – | – | – |
| `qc_operator` | Y | – | Y | Y | – | – | – | – | – |
| `content_manager` | Y | – | – | – | Y | Y | request | request | – |
| `rights_manager` | Y | – | – | – | rights | – | – | Y | – |
| `admin` | Y | Y | Y | Y | Y | Y | Y | Y | Y |

**Approval flow**: Publish requires (a) QC pass, (b) rights manager confirming licensed territories + dates, (c) content manager sign-off. Access granted on business-need basis (Starship) — scoped grants per title/series, not just global roles.

## 6. Bulk operations + import + industry standard formats

Bulk: Backlot Source Requests API (REST), CSV metadata import, MEC XML for industry interchange.

Standards — one-liners:

- **EIDR** — global unique ID (DOI-based URN) for A/V work. Use as canonical `external_id` on the title.
- **IMF (SMPTE ST 2067)** — XML-described package: video/audio/sub Track Files + Composition Playlists. Netflix mandates Application 2E.
- **IMSC 1.1 (W3C, TTML profile)** — XML subtitle/caption with rich styling + ruby/vertical text; Netflix mandates for Japanese.
- **BXF (SMPTE ST 2021)** — XML for schedules, as-run logs, content metadata, rights between traffic/automation systems. More for linear-broadcast-adjacent OTT.
- **MovieLabs Common Metadata + MEC** — descriptive title metadata (synopsis, cast, ratings, genres, localized variants).
- **MovieLabs MMC** — maps metadata to physical assets in a delivery.
- **Avails** — XML/Excel describing rights windows per territory per platform.

## 7. Audit log expectations

Netflix's **Data Canary** runs baseline + canary clusters of the catalog service, replays production traffic, blocks bad mutations from reaching members in <10 min. Implies every catalog mutation is versioned, diffable, reversible. Spec: append-only `audit_log` `(actor_user_id, role, action, entity_type, entity_id, before_jsonb, after_jsonb, request_id, ts)`. Catalog publishes are versioned snapshots, not in-place writes. Backlot exposes per-asset change logs + timecoded QC issue history.

## 8. Soft-delete + restoration

Netflix removes titles when licenses expire; downloads invalidate immediately at catalog-version boundary. Model: titles get `availability_status = removed` + `effective_until = <license_end>`, never row deletion. Rights stored per `(title_id, region, start_at, end_at, license_id)`; renewed license inserts new row. Asset binaries governed by lifecycle policy engine (Policy Manager) — assets transition `hot → warm → cold/glacier → purge`; restoration is policy-triggered cold→hot. Always keep metadata even when blob is archived.

## 9. Sources

- Netflix TechBlog: Production Media Management, Globalizing Productions with MPS, IMF Prescription for Versionitis, NMDB, A/B Artwork Testing, Artwork Personalization, Data Canary, Cloud Lifecycle
- Netflix Partner Help: Backlot Overview, 2023 Backlot Remodel, IMF Overview, IMF Delivery & Inspections, IMSC 1.1 Text Profile, Quality Control, Content Hub Introduction, InfoSec Guidebook
- Netflix Backlot API Docs (public)
- Netflix Help: Why titles leave Netflix, How Netflix licenses
- EIDR, IMF, MovieLabs (Common Metadata, MEC v2.12, MMC) standards
- MDN — IMSC, Wikipedia — Broadcast Exchange Format
- Variety — Netflix A/B Tests; InfoQ — Netflix Upper Metamodel; TVTech — Media Production Suite; Moltencloud — Netflix Delivery Guide; Vitrina — Acquisition Strategy
