# Netflix Catalog, Browse & Recommendation Research

**Date:** 2026-06-02
**Purpose:** Source material for ADR-0002. This is the raw research output; ADR-0002 is the digested decisions.

---

## 1. Content types and hierarchy

Netflix's catalog effectively has two top-level `content_type` values:

- **movie** — single playable asset, has a `runtime` in minutes.
- **series** — has `seasons[]`, each with `episodes[]`. Episode is the playable unit.

**Mini-series / limited series** are NOT a separate `content_type`. They are modelled as a series with a single season and a `series_subtype = "limited"` flag. Industry convention: 2–13 self-contained episodes, one season, story concludes. Schema implication: an enum `series_type` in {`ongoing`,`limited`,`anthology`} on the series row is sufficient — same `seasons → episodes` tree.

**Specials, stand-up, documentaries** are not their own content_type. They are either:
- A movie with one or more `genres` tags (e.g., `Stand-Up Comedy`, `Documentary`), or
- A series with the same genre tags (`Docuseries`).

Recommendation: model `content_type ∈ {movie, series}` only, then carry `genres[]` and an optional `format_tag ∈ {standup, documentary, special, concert, ...}` as a denormalized flag for fast filtering.

**Hierarchy:**
```
title (id, type=movie|series)
 └─ if series: season (id, title_id, season_number, name)
                └─ episode (id, season_id, episode_number, name, runtime, intro_marker, recap_marker, credits_marker)
```

## 2. Per-title metadata (data model implications)

Per **title** (movie or series):

- `original_language` — single ISO 639-1 string (the production language).
- `audio_tracks[]` — list of `{language, type ∈ (original|dub), codec?}`. Netflix supports ~36 dub languages.
- `subtitle_tracks[]` — list of `{language, type ∈ (subtitle|cc|sdh|dubtitle), forced: bool}`. ~33 subtitle languages.
- `maturity_ratings[]` — per-country, list of `{country_code, system, rating_code, maturity_level (int 0–18 normalized)}`. Netflix has an internal 6-tier ladder (All, 7+, 10+, 13+, 16+, 18+) that maps regional codes to one normalized value.
- `cast[]` — `{person_id, character_name, order}`. Ordered.
- `crew[]` — `{person_id, role ∈ (director, writer, creator, producer, ...)}`.
- `genres[]` — many-to-many; Netflix has a deep tag taxonomy (the "secret codes" — thousands of micro-genres).
- `runtime_minutes` — for movies only; for series, runtime is per-episode.
- `release_year`, `country_of_origin[]` (list — co-productions exist).
- `availability[]` — `{country_code, available_from, available_until}` (regional licensing).
- `artwork[]` — list of `{asset_id, image_url, locale, aspect, tags[]}`. Multiple per title; one picked per user per request by image personalization service.

**Match score** is per-user, computed at request time. Returned alongside title as `match_score: int 0–100`. Source is the PVR's predicted-relevance score, rescaled.

## 3. Browse rows (each with 1-line trigger)

| Row | Trigger / source |
|---|---|
| Continue Watching | In-progress watch (>start, <~95%). Ordered by CWR. |
| Watch It Again | Finished titles predicted likely to re-watch. |
| Top Picks for [name] | Top-N Video Ranker output. |
| Trending Now | Trending Now Ranker; short-window popularity, region-weighted. |
| Top 10 in [country] | Daily-refreshed top 10 by country; same ordering for everyone in that country. |
| New Releases | `available_from` within last ~30 days, region. |
| New & Popular | Hybrid: new releases ranked by early-engagement signal. |
| Because You Watched X | Video-Video Similarity, seeded by a specific recent watch. |
| My List | User-added titles. |
| Per-genre rows | PVR-personalized order within a genre bucket. |
| Coming Soon | Future `available_from` in user's region. |
| Award-Winning | Tag-filtered; PVR-ordered. |
| Top 10 TV / Movies | Same as Top 10 split by type. |

~40 rows per homepage, up to ~75 titles per row. Row set + vertical order itself personalized by "Evidence & Row Selection".

## 4. Filters and sorts

**Filters:** Genre (single-select), Original language, Subtitle language, Dubbing language, Release year/decade, Audience.

**Sort options:** Suggestions For You (default, PVR), Year Released (newest first), A–Z / Z–A (intermittently available). Sort is web-only; mobile/TV apps default to personalized order.

## 5. User-driven preferences

- **Three-state reaction** (per-profile, per-title): `reaction ∈ {thumbs_down, thumbs_up, double_thumbs_up, null}`. Introduced April 2022. Unique on `(profile_id, title_id)`.
- **My List** (per-profile watchlist). Default ordering algorithmic. Filter options: by type, by status, by date added, alphabetical. Drag-to-reorder not consistently available.
- **Taste seeds**: onboarding picks 3+ liked titles to bootstrap cold-start PVR.
- **Hidden from history**: marks suppress Continue Watching + reduce rec influence.

## 6. Recommendation systems (Netflix's named rankers)

- **Personalized Video Ranker (PVR)** — Ranks the entire catalog per profile; substrate for genre-row ordering and themed rows.
- **Top N Video Ranker** — Picks absolute top titles for the "Top Picks for You" row.
- **Trending Now Ranker** — Short-window popularity + personalization; reacts to seasonal/real-world events.
- **Continue Watching Ranker (CWR)** — Orders partially-watched titles. Two sub-models: Show Ranking, Row Placement.
- **Video-Video Similarity / BYW** — Item-based CF; precomputed similarity per item; surfaced seeded by recent watches.
- **Image / Artwork Personalization** — Contextual bandit; picks artwork per user per session. Cited as driving 80% of viewing decisions.
- **Evidence Selection** — Which snippet ("Because Idris Elba is in it", "97% match") to show.
- **Page Generation / Row Selection** — Which rows + vertical order; itself personalized.

## 7. Episode-level behaviours

- **Episode order**: `(season_number, episode_number)` integers; for Netflix originals, same as air date.
- **Watch progress per episode**: `watch_progress (profile_id, episode_id_or_movie_id, position, duration, updated_at, device_id)`. "Finished" at ~90–95%.
- **Skip Intro / Recap / Credits**: per-episode markers stored as `intro_start/end_sec`, `recap_start/end_sec`, `credits_start_sec` (all nullable).
- **Next-episode cue**: `next_episode_cue_sec` (when post-play card appears).
- **Auto-play next episode**: profile-level boolean `autoplay_next`.
- **Auto-play previews**: separate boolean `autoplay_previews`.

## 8. Sources

- Netflix Tech Blog (Artwork Personalization, Interleaving)
- Netflix Research (Recommendations area)
- New America OTI — Netflix Case Study (named rankers)
- Netflix Help (Ratings, Maturity ratings, Search & browse)
- Netflix Tudum (Homepage layout)
- Netflix Top 10 site (Top 10 country lists)
- About Netflix / Variety (Two Thumbs Up launch)
- Tom's Guide / TechHive (Search filter changes, My List)
- What's on Netflix (Category codes / genre taxonomy)
- Netflix Partner Help (Localization & Dubbing branded delivery specs)
- TMDB API (TV Series Details reference)
- USC Illumin (Recommendation Systems writeup)
- Medium — Netflix Resume bookmark store
