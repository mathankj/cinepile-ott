# Database schema — V1.5

> **Source of truth:** the SQLAlchemy models in `backend/app/models/`. This document explains *why* each table looks the way it does. When the code diverges, the code wins — open a PR to fix this doc.

All tables: `id BIGINT PK`, `created_at TIMESTAMPTZ DEFAULT now()`, `updated_at TIMESTAMPTZ DEFAULT now()` unless noted. Soft-deletable tables also have `deleted_at TIMESTAMPTZ NULL`.

---

## Auth / users

### users

| Column | Type | Notes |
|---|---|---|
| email | CITEXT UNIQUE NOT NULL | case-insensitive |
| password_hash | TEXT NOT NULL | bcrypt (SHA-256 prehash for >72-byte safety) |
| full_name | TEXT | |
| role | TEXT NOT NULL DEFAULT 'user' | `user` \| `viewer` \| `content_manager` \| `admin` |
| is_active | BOOLEAN NOT NULL DEFAULT true | |
| session_version | INT NOT NULL DEFAULT 1 | bump to invalidate all outstanding tokens |
| email_verified_at | TIMESTAMPTZ NULL | |

### refresh_tokens

(unchanged from V1) UUID PK; sha256 hash of token; family + rotation tracking; `replaced_by_id` for reuse-detection.

## Catalog — Titles, Seasons, Episodes

### titles

The "unified content" table — movies + series share this row.

| Column | Type | Notes |
|---|---|---|
| slug | TEXT UNIQUE NOT NULL | url-friendly |
| type | TEXT NOT NULL | `movie` \| `series` |
| series_type | TEXT NULL | for `type=series` only: `ongoing` \| `limited` \| `mini` \| `anthology` |
| title | TEXT NOT NULL | |
| original_title | TEXT NULL | |
| synopsis | TEXT NULL | |
| release_year | INT NULL | |
| runtime_minutes | INT NULL | movies only; for series this is per-episode |
| age_rating | TEXT NULL | single normalized rating like `U`, `U/A`, `A`, `12+`, `16+`, `18+` |
| original_language | TEXT NULL | ISO 639-1 of production language |
| countries | JSON NULL | list of ISO 3166-1 alpha-2 (co-productions exist) |
| poster_url | TEXT NULL | |
| backdrop_url | TEXT NULL | |
| trailer_url | TEXT NULL | |
| format_tag | TEXT NULL | optional: `standup` \| `documentary` \| `concert` \| `special` |
| status | TEXT NOT NULL DEFAULT 'draft' | `draft` \| `scheduled` \| `published` \| `archived` \| `removed` |
| publish_at | TIMESTAMPTZ NULL | for `status=scheduled`, when to flip to `published` |
| published_at | TIMESTAMPTZ NULL | actual time it went live |
| view_count | BIGINT NOT NULL DEFAULT 0 | denormalized counter for trending; incremented in `playback.issue_ticket` |
| deleted_at | TIMESTAMPTZ NULL | soft-delete |

Indexes: `slug` unique, `(status, published_at)` for default listings, `(type, status)`, `view_count DESC` for trending, GIN on `synopsis||title` (Postgres) for search (deferred — V1.5 uses LIKE).

### seasons

(Series only.) One row per season.

| Column | Type | Notes |
|---|---|---|
| title_id | BIGINT FK titles ON DELETE CASCADE | series this season belongs to |
| season_number | INT NOT NULL | 1-indexed |
| name | TEXT NULL | "Season 1" or "Vol. 1 — The Setup" |
| synopsis | TEXT NULL | optional season-level synopsis |
| poster_url | TEXT NULL | season-specific poster (optional, falls back to series) |
| release_year | INT NULL | first-episode year |

Unique constraint: `(title_id, season_number)`.

### episodes

(Series only.) The playable unit for series.

| Column | Type | Notes |
|---|---|---|
| season_id | BIGINT FK seasons ON DELETE CASCADE | |
| episode_number | INT NOT NULL | within the season |
| ordinal | INT NOT NULL | sort key (usually = episode_number; mutable for re-cuts) |
| name | TEXT NOT NULL | |
| synopsis | TEXT NULL | |
| runtime_seconds | INT NULL | actual duration once known |
| air_date | DATE NULL | original air date |
| intro_start_sec | INT NULL | skip-intro marker |
| intro_end_sec | INT NULL | |
| recap_start_sec | INT NULL | skip-recap marker |
| recap_end_sec | INT NULL | |
| credits_start_sec | INT NULL | end credits begin |
| next_episode_cue_sec | INT NULL | when post-play card appears |
| status | TEXT NOT NULL DEFAULT 'draft' | independent of parent title status (weekly releases) |
| publish_at | TIMESTAMPTZ NULL | |
| published_at | TIMESTAMPTZ NULL | |

Unique constraint: `(season_id, episode_number)`. Index on `(season_id, ordinal)`.

### genres + titles_genres

| genres | |
|---|---|
| slug | TEXT UNIQUE NOT NULL |
| name | TEXT NOT NULL |
| kind | TEXT NOT NULL DEFAULT 'primary' | `primary` \| `sub` \| `mood` |

Many-to-many junction: `titles_genres (title_id, genre_id) PK`.

### persons + title_credits

| persons | |
|---|---|
| name | TEXT NOT NULL |
| profile_url | TEXT NULL |

| title_credits | |
|---|---|
| title_id | FK titles |
| person_id | FK persons |
| role | TEXT NOT NULL | `cast` \| `director` \| `writer` \| `creator` \| `producer` |
| character_name | TEXT NULL | for `role=cast` |
| order | INT NOT NULL DEFAULT 0 | display order |

### audio_tracks

One row per available audio track per title.

| Column | Type | Notes |
|---|---|---|
| title_id | FK titles ON DELETE CASCADE | |
| language | TEXT NOT NULL | ISO 639-1 |
| kind | TEXT NOT NULL | `original` \| `dub` |
| codec | TEXT NULL | optional info |

Index `(title_id, language)`.

### subtitle_tracks

| Column | Type | Notes |
|---|---|---|
| title_id | FK titles ON DELETE CASCADE | |
| language | TEXT NOT NULL | ISO 639-1 |
| kind | TEXT NOT NULL | `subtitle` \| `cc` \| `sdh` \| `dubtitle` |
| forced | BOOLEAN NOT NULL DEFAULT false | "forced narratives" — translates foreign-language dialogue in an otherwise-original-language film |

### availability_windows

Per-region licensing window. Replaces a single published_at when the client launches in multiple regions.

| Column | Type | Notes |
|---|---|---|
| title_id | FK titles | |
| country_code | TEXT NOT NULL | ISO 3166 alpha-2 |
| starts_at | TIMESTAMPTZ NOT NULL | |
| ends_at | TIMESTAMPTZ NULL | NULL = open-ended |

Index `(title_id, country_code)`.

### maturity_ratings (optional override table)

For titles where the global `age_rating` doesn't apply uniformly.

| Column | Type | Notes |
|---|---|---|
| title_id | FK titles | |
| country_code | TEXT NOT NULL | |
| system | TEXT NOT NULL | `MPAA` \| `BBFC` \| `CBFC` \| `TV` ... |
| rating_code | TEXT NOT NULL | e.g. `PG-13`, `TV-MA`, `15` |
| maturity_level | INT NOT NULL | 0–18 normalized for parental-controls comparison |

### title_assets / episode_assets

V1's `film_assets` → two tables. Title-level (for movies, for series trailers) vs episode-level (per-episode HLS manifests).

| title_assets | |
|---|---|
| title_id | FK titles |
| kind | `hls_manifest` \| `trailer` |
| storage_url | TEXT NOT NULL |
| language | TEXT NULL |

| episode_assets | |
|---|---|
| episode_id | FK episodes |
| kind | `hls_manifest` |
| storage_url | TEXT NOT NULL |

## User actions

### reactions

| Column | Type | Notes |
|---|---|---|
| user_id | FK users ON DELETE CASCADE | |
| title_id | FK titles ON DELETE CASCADE | |
| kind | TEXT NOT NULL | `thumbs_down` \| `thumbs_up` \| `double_thumbs_up` |

Unique constraint: `(user_id, title_id)`. Switching reaction = upsert.

### watchlist_items

| Column | Type | Notes |
|---|---|---|
| user_id | FK users ON DELETE CASCADE | |
| title_id | FK titles ON DELETE CASCADE | |
| added_at | TIMESTAMPTZ NOT NULL | for ordering |

Unique constraint: `(user_id, title_id)`.

### watch_progress

Per-user, per-watchable. Replaces V1's `watch_history`.

| Column | Type | Notes |
|---|---|---|
| user_id | FK users ON DELETE CASCADE | |
| title_id | FK titles ON DELETE CASCADE | always set (the movie or the series) |
| episode_id | FK episodes ON DELETE CASCADE NULL | set only for series episodes |
| position_sec | INT NOT NULL DEFAULT 0 | |
| total_sec | INT NOT NULL DEFAULT 0 | |
| completed | BOOLEAN NOT NULL DEFAULT false | true when `position_sec / total_sec >= 0.9` |
| last_played_at | TIMESTAMPTZ NOT NULL | for continue-watching ordering |

Unique constraint: `(user_id, title_id, episode_id)`. SQLite treats NULL as distinct in unique indexes (same as Postgres). Indexes: `(user_id, last_played_at DESC)`.

## Subscriptions (unchanged from V1)

`plans` and `subscriptions` as documented in V1. Untouched.

## Audit log

Every catalog mutation by an admin writes one row here. Append-only.

| Column | Type | Notes |
|---|---|---|
| actor_user_id | FK users | |
| actor_role | TEXT NOT NULL | snapshot of role at write time |
| action | TEXT NOT NULL | e.g. `title.create`, `title.publish`, `title.archive`, `episode.create`, `user.role_change` |
| entity_type | TEXT NOT NULL | `title` \| `episode` \| `user` |
| entity_id | BIGINT NOT NULL | |
| before | JSON NULL | snapshot before (for updates) |
| after | JSON NULL | snapshot after (for creates/updates) |
| request_id | TEXT NULL | correlates with the X-Request-ID header |

Indexes: `(entity_type, entity_id)`, `(actor_user_id, created_at DESC)`.

---

## ERD (rough)

```
users ──< refresh_tokens
users ──< subscriptions >── plans
users ──< watch_progress >── titles
                        └─< episodes
users ──< reactions    >── titles
users ──< watchlist    >── titles
users ──< audit_log

titles ──< seasons ──< episodes ──< episode_assets
titles ──< title_assets
titles >─< genres            (via titles_genres)
titles ──< title_credits >── persons
titles ──< audio_tracks
titles ──< subtitle_tracks
titles ──< availability_windows
titles ──< maturity_ratings
```

## Migrations

V1.5 introduces Alembic. The dev DB is dropped and recreated from migration `0001_initial`. Going forward, every schema change is a new migration; we never edit applied migrations.
