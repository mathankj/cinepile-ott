# Database schema — V1

All tables: `id BIGINT PK`, `created_at TIMESTAMPTZ DEFAULT now()`, `updated_at TIMESTAMPTZ DEFAULT now()` unless noted. Soft-deletable tables also have `deleted_at TIMESTAMPTZ NULL`.

---

## users

| Column | Type | Notes |
|---|---|---|
| id | BIGINT PK | |
| email | CITEXT UNIQUE NOT NULL | case-insensitive |
| password_hash | TEXT NOT NULL | bcrypt |
| full_name | TEXT | |
| role | TEXT NOT NULL DEFAULT 'user' | `user` \| `admin` |
| is_active | BOOLEAN NOT NULL DEFAULT true | |
| session_version | INT NOT NULL DEFAULT 1 | bump to invalidate all existing refresh tokens for this user |
| email_verified_at | TIMESTAMPTZ NULL | |

Indexes: unique on `email`. Index on `role` (admin lookups are rare but cheap).

## refresh_tokens

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| user_id | FK users | |
| token_hash | TEXT NOT NULL | SHA-256 of the raw token; never store raw |
| family_id | UUID NOT NULL | shared across rotations of a single session |
| issued_at | TIMESTAMPTZ | |
| expires_at | TIMESTAMPTZ NOT NULL | |
| revoked_at | TIMESTAMPTZ NULL | |
| replaced_by_id | UUID FK refresh_tokens NULL | for rotation audit trail |

Indexes: `(user_id, family_id)`, `expires_at` (for periodic cleanup).

## plans

| Column | Type | Notes |
|---|---|---|
| id | BIGINT PK | |
| code | TEXT UNIQUE NOT NULL | `monthly`, `annual`, etc. |
| name | TEXT NOT NULL | display name |
| price_cents | INT NOT NULL | currency-agnostic; convert in service layer |
| currency | TEXT NOT NULL DEFAULT 'INR' | ISO 4217 |
| billing_interval | TEXT NOT NULL | `month` \| `year` |
| is_active | BOOLEAN NOT NULL DEFAULT true | |

## subscriptions

| Column | Type | Notes |
|---|---|---|
| id | BIGINT PK | |
| user_id | FK users | |
| plan_id | FK plans | |
| status | TEXT NOT NULL | `active` \| `cancelled` \| `expired` \| `past_due` |
| current_period_start | TIMESTAMPTZ NOT NULL | |
| current_period_end | TIMESTAMPTZ NOT NULL | |
| cancel_at_period_end | BOOLEAN NOT NULL DEFAULT false | |
| provider | TEXT NOT NULL DEFAULT 'mock' | `mock` \| `razorpay` \| `stripe` |
| provider_subscription_id | TEXT NULL | filled when integrated |

Indexes: `(user_id, status)`, `current_period_end` (for renewal/expiry cron).

## films

| Column | Type | Notes |
|---|---|---|
| id | BIGINT PK | |
| slug | TEXT UNIQUE NOT NULL | url-friendly |
| title | TEXT NOT NULL | |
| original_title | TEXT NULL | |
| synopsis | TEXT | |
| release_year | INT | |
| runtime_minutes | INT | |
| age_rating | TEXT | `U`, `U/A`, `A`, `12+`, etc. |
| poster_url | TEXT | |
| backdrop_url | TEXT | |
| trailer_url | TEXT NULL | |
| primary_language | TEXT | ISO 639 |
| countries | TEXT[] | ISO 3166 |
| status | TEXT NOT NULL DEFAULT 'draft' | `draft` \| `published` \| `archived` |
| published_at | TIMESTAMPTZ NULL | |
| search_vector | TSVECTOR | maintained by trigger; powers `/v1/films/search` |
| deleted_at | TIMESTAMPTZ NULL | soft delete |

Indexes: `slug` unique, GIN on `search_vector`, `(status, published_at)` for default listings.

## film_assets

| Column | Type | Notes |
|---|---|---|
| id | BIGINT PK | |
| film_id | FK films | |
| kind | TEXT NOT NULL | `master_video`, `hls_manifest`, `subtitle`, `audio` |
| storage_url | TEXT NOT NULL | S3-style path; not directly served |
| language | TEXT NULL | for subtitles/audio |
| bitrate_kbps | INT NULL | for video variants |
| width | INT NULL | |
| height | INT NULL | |
| duration_sec | INT NULL | |

Phase 2 fills this in via the transcoding pipeline. Phase 1 stores one row per film pointing at a sample HLS manifest URL.

## categories + films_categories

Many-to-many. Categories: id, slug, name. Junction: (film_id, category_id) PK.

## watch_history

| Column | Type | Notes |
|---|---|---|
| user_id | FK users | |
| film_id | FK films | |
| position_sec | INT NOT NULL | |
| total_sec | INT NOT NULL | |
| completed | BOOLEAN NOT NULL DEFAULT false | `position_sec / total_sec > 0.9` |
| last_played_at | TIMESTAMPTZ NOT NULL | |

PK: `(user_id, film_id)`. Index `(user_id, last_played_at DESC)` for continue-watching.

---

## ERD (rough)

```
users ──< refresh_tokens
users ──< subscriptions >── plans
users ──< watch_history >── films
films ──< film_assets
films >─< categories       (via films_categories)
```

## Migration strategy

- One Alembic migration per logical change. Never amend an applied migration.
- Every migration must have a working `downgrade()` (or be explicit: "irreversible, see runbook").
- Schema changes that lock tables go through the runbook in `docs/runbooks/safe-migrations.md` (to be written when we hit one).
