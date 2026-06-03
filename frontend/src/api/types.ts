/**
 * Shared TypeScript types matching the backend's Pydantic schemas.
 * Keep these in sync with backend/app/schemas/*.py — when in doubt, regen
 * from the live OpenAPI at GET /openapi.json (`npx openapi-typescript`).
 */

export type TitleType = "movie" | "series";
export type SeriesType = "ongoing" | "limited" | "mini" | "anthology";
export type TitleStatus = "draft" | "scheduled" | "published" | "archived" | "removed";

export type Genre = { id: number; slug: string; name: string; kind: string };

export type AudioTrack = { language: string; kind: "original" | "dub"; codec?: string | null };
export type SubtitleTrack = {
  language: string;
  kind: "subtitle" | "cc" | "sdh" | "dubtitle";
  forced: boolean;
};

export type Person = { id: number; name: string; profile_url?: string | null };
export type Credit = {
  person: Person;
  role: "cast" | "director" | "writer" | "creator" | "producer";
  character_name?: string | null;
  order: number;
};

export type TitleAsset = { kind: string; storage_url: string; language?: string | null };
export type EpisodeAsset = { kind: string; storage_url: string };

export type TitleSummary = {
  id: number;
  slug: string;
  type: TitleType;
  title: string;
  poster_url: string | null;
  backdrop_url: string | null;
  release_year: number | null;
  age_rating: string | null;
  runtime_minutes: number | null;
  is_free: boolean;
};

export type SeasonSummary = {
  id: number;
  season_number: number;
  name: string | null;
  episode_count: number;
};

export type TitleDetail = TitleSummary & {
  series_type: SeriesType | null;
  original_title: string | null;
  synopsis: string | null;
  original_language: string | null;
  countries: string[] | null;
  trailer_url: string | null;
  format_tag: string | null;
  status: TitleStatus;
  published_at: string | null;
  view_count: number;
  genres: Genre[];
  audio_tracks: AudioTrack[];
  subtitle_tracks: SubtitleTrack[];
  credits: Credit[];
  assets: TitleAsset[];
  seasons: SeasonSummary[];
};

export type Episode = {
  id: number;
  episode_number: number;
  ordinal: number;
  name: string;
  synopsis: string | null;
  runtime_seconds: number | null;
  air_date: string | null;
  intro_start_sec: number | null;
  intro_end_sec: number | null;
  recap_start_sec: number | null;
  recap_end_sec: number | null;
  credits_start_sec: number | null;
  next_episode_cue_sec: number | null;
  status: TitleStatus;
  published_at: string | null;
  is_free: boolean;
  assets: EpisodeAsset[];
};

export type SeasonDetail = {
  id: number;
  season_number: number;
  name: string | null;
  synopsis: string | null;
  poster_url: string | null;
  release_year: number | null;
  episodes: Episode[];
};

export type TitleListResponse = {
  items: TitleSummary[];
  page: number;
  page_size: number;
  total: number;
};

export type PlaybackTicket = {
  manifest_url: string;
  token: string;
  expires_at: string;
  ref_type: "title" | "episode";
  ref_id: number;
  resume_at_sec: number | null;
  total_sec: number | null;
};

export type HomeRow = {
  kind: string;
  title: string;
  items: TitleSummary[];
};

export type ContinueWatchingItem = {
  title: TitleSummary;
  episode_id: number | null;
  episode_number: number | null;
  season_number: number | null;
  episode_name: string | null;
  position_sec: number;
  total_sec: number;
  last_played_at: string;
};

export type HistoryItem = {
  title: TitleSummary;
  position_sec: number;
  total_sec: number;
  completed: boolean;
  hidden_from_continue: boolean;
  last_played_at: string;
};

export type WatchlistItemRead = { title: TitleSummary; added_at: string };

export type ReactionKind = "thumbs_down" | "thumbs_up" | "double_thumbs_up";
export type ReactionRead = { title: TitleSummary; kind: ReactionKind; updated_at: string };

export type Plan = {
  id: number;
  code: string;
  name: string;
  price_cents: number;
  currency: string;
  billing_interval: "month" | "year";
};

export type Subscription = {
  id: number;
  plan_id: number;
  status: "pending" | "active" | "past_due" | "cancelled" | "expired";
  current_period_start: string;
  current_period_end: string;
  cancel_at_period_end: boolean;
  provider: string;
  checkout_url: string | null;
};

export type TokenPair = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_at: string;
};

export type AuthSuccess = {
  tokens: TokenPair;
  user: {
    id: number;
    email: string;
    full_name: string | null;
    role: "user" | "viewer" | "content_manager" | "admin";
    is_active: boolean;
    created_at: string;
  };
};
