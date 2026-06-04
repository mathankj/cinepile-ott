/**
 * Typed API wrapper. One function per endpoint. Components call these via
 * TanStack Query hooks in src/hooks/.
 */
import { api } from "./client";
import type {
  AuthSuccess,
  ContinueWatchingItem,
  Episode,
  HistoryItem,
  HomeRow,
  Plan,
  PlaybackTicket,
  Profile,
  ProfileList,
  ReactionKind,
  ReactionRead,
  SeasonDetail,
  Subscription,
  TitleDetail,
  TitleListResponse,
  TitleSummary,
  TokenPair,
  WatchlistItemRead,
} from "./types";

// ---------- Auth ----------

export const auth = {
  signup: (email: string, password: string, full_name?: string | null) =>
    api.post<AuthSuccess>("/v1/auth/signup", { email, password, full_name }).then((r) => r.data),

  login: (email: string, password: string) =>
    api.post<AuthSuccess>("/v1/auth/login", { email, password }).then((r) => r.data),

  refresh: (refresh_token: string) =>
    api.post<TokenPair>("/v1/auth/refresh", { refresh_token }).then((r) => r.data),

  logout: (refresh_token: string) => api.post("/v1/auth/logout", { refresh_token }),

  me: () => api.get<AuthSuccess["user"]>("/v1/auth/me").then((r) => r.data),
};

// ---------- Catalog ----------

export const catalog = {
  listTitles: (params: {
    type?: "movie" | "series";
    genre?: string;
    language?: string;
    country?: string;
    year_from?: number;
    year_to?: number;
    sort?: string;
    page?: number;
    page_size?: number;
  } = {}) =>
    api.get<TitleListResponse>("/v1/titles", { params }).then((r) => r.data),

  comingSoon: (limit = 20) =>
    api.get<TitleSummary[]>("/v1/titles/coming-soon", { params: { limit } }).then((r) => r.data),

  search: (q: string) =>
    api.get<TitleSummary[]>("/v1/titles/search", { params: { q } }).then((r) => r.data),

  detail: (id: number) => api.get<TitleDetail>(`/v1/titles/${id}`).then((r) => r.data),

  season: (titleId: number, seasonNumber: number) =>
    api.get<SeasonDetail>(`/v1/titles/${titleId}/seasons/${seasonNumber}`).then((r) => r.data),

  episode: (titleId: number, seasonNumber: number, episodeNumber: number) =>
    api
      .get<Episode>(`/v1/titles/${titleId}/seasons/${seasonNumber}/episodes/${episodeNumber}`)
      .then((r) => r.data),

  trailer: (titleId: number) =>
    api
      .get<{ title_id: number; trailer_url: string; source: string }>(
        `/v1/titles/${titleId}/trailer`
      )
      .then((r) => r.data),

  genres: () =>
    api
      .get<{ id: number; slug: string; name: string; kind: string }[]>("/v1/home/genres")
      .then((r) => r.data),
};

// ---------- Playback ----------

export const playback = {
  movie: (titleId: number) =>
    api.get<PlaybackTicket>(`/v1/titles/${titleId}/play`).then((r) => r.data),

  episode: (episodeId: number) =>
    api.get<PlaybackTicket>(`/v1/episodes/${episodeId}/play`).then((r) => r.data),
};

// ---------- Watch progress + Continue Watching ----------

export const progress = {
  postMovie: (titleId: number, position_sec: number, total_sec: number) =>
    api.post(`/v1/titles/${titleId}/progress`, { position_sec, total_sec }),

  postEpisode: (episodeId: number, position_sec: number, total_sec: number) =>
    api.post(`/v1/episodes/${episodeId}/progress`, { position_sec, total_sec }),

  continueWatching: () =>
    api.get<{ items: ContinueWatchingItem[] }>("/v1/me/continue-watching").then((r) => r.data),

  hideFromContinue: (titleId: number) => api.delete(`/v1/me/continue-watching/${titleId}`),

  history: (page = 1, page_size = 20) =>
    api
      .get<{ items: HistoryItem[]; page: number; page_size: number; total: number }>(
        "/v1/me/history",
        { params: { page, page_size } }
      )
      .then((r) => r.data),

  deleteHistory: (titleId: number) => api.delete(`/v1/me/history/${titleId}`),
};

// ---------- Reactions + My List ----------

export const me = {
  setReaction: (titleId: number, kind: ReactionKind) =>
    api.put(`/v1/titles/${titleId}/reaction`, { kind }),

  clearReaction: (titleId: number) => api.delete(`/v1/titles/${titleId}/reaction`),

  reactions: () =>
    api.get<{ items: ReactionRead[] }>("/v1/me/reactions").then((r) => r.data),

  addToList: (titleId: number) =>
    api.post<{ title_id: number; added: boolean }>(`/v1/me/list/${titleId}`).then((r) => r.data),

  removeFromList: (titleId: number) => api.delete(`/v1/me/list/${titleId}`),

  listWatchlist: () =>
    api.get<{ items: WatchlistItemRead[] }>("/v1/me/list").then((r) => r.data),

  // ---------- Recommendations ----------
  recommendations: () =>
    api.get<TitleSummary[]>("/v1/me/recommendations").then((r) => r.data),

  // ---------- Profiles ("Who's watching?") ----------
  listProfiles: () => api.get<ProfileList>("/v1/me/profiles").then((r) => r.data),
  createProfile: (body: { name: string; avatar?: string; kind?: "adult" | "kid" }) =>
    api.post<Profile>("/v1/me/profiles", body).then((r) => r.data),
  updateProfile: (
    id: number,
    body: { name?: string; avatar?: string; kind?: "adult" | "kid" },
  ) => api.patch<Profile>(`/v1/me/profiles/${id}`, body).then((r) => r.data),
  deleteProfile: (id: number) => api.delete(`/v1/me/profiles/${id}`),
};

// ---------- Home rows ----------

export const home = {
  get: (country?: string) =>
    api
      .get<{ rows: HomeRow[] }>("/v1/home", { params: country ? { country } : undefined })
      .then((r) => r.data),
};

// ---------- Subscriptions / Billing ----------

export const billing = {
  plans: () => api.get<Plan[]>("/v1/plans").then((r) => r.data),
  mySubscription: () =>
    api.get<Subscription | null>("/v1/subscriptions/me").then((r) => r.data),
  subscribe: (plan_code: string) =>
    api.post<Subscription>("/v1/subscriptions", { plan_code }).then((r) => r.data),
  cancel: () =>
    api
      .post<{ subscription: Subscription; message: string }>("/v1/subscriptions/cancel")
      .then((r) => r.data),
  verifyPayment: (
    razorpay_order_id: string,
    razorpay_payment_id: string,
    razorpay_signature: string
  ) =>
    api
      .post<Subscription>("/v1/payments/verify", {
        razorpay_order_id,
        razorpay_payment_id,
        razorpay_signature,
      })
      .then((r) => r.data),
};

// ---------- Admin (used by admin UI) ----------

export const admin = {
  // Titles
  createTitle: (body: Record<string, unknown>) =>
    api.post<TitleDetail>("/v1/admin/titles", body).then((r) => r.data),
  getTitle: (id: number) =>
    api.get<TitleDetail>(`/v1/admin/titles/${id}`).then((r) => r.data),
  updateTitle: (id: number, body: Record<string, unknown>) =>
    api.patch<TitleDetail>(`/v1/admin/titles/${id}`, body).then((r) => r.data),
  publishTitle: (id: number) =>
    api.post<TitleDetail>(`/v1/admin/titles/${id}/publish`).then((r) => r.data),
  scheduleTitle: (id: number, publish_at: string) =>
    api
      .post<TitleDetail>(`/v1/admin/titles/${id}/schedule`, { publish_at })
      .then((r) => r.data),
  archiveTitle: (id: number) =>
    api.post<TitleDetail>(`/v1/admin/titles/${id}/archive`).then((r) => r.data),
  deleteTitle: (id: number) => api.delete(`/v1/admin/titles/${id}`),
  uploadTitleVideo: (id: number, file: File, onProgress?: (pct: number) => void) => {
    const data = new FormData();
    data.append("file", file);
    return api.post<{
      title_id: number;
      key: string;
      stored_ref: string;
      playable_url: string;
    }>(`/v1/admin/titles/${id}/upload-video`, data, {
      headers: { "Content-Type": "multipart/form-data" },
      onUploadProgress: (e) => {
        if (e.total && onProgress) onProgress(Math.round((e.loaded / e.total) * 100));
      },
    }).then((r) => r.data);
  },

  // Seasons + Episodes
  createSeason: (titleId: number, body: { season_number: number; name?: string }) =>
    api.post(`/v1/admin/titles/${titleId}/seasons`, body).then((r) => r.data),
  createEpisode: (seasonId: number, body: Record<string, unknown>) =>
    api.post(`/v1/admin/seasons/${seasonId}/episodes`, body).then((r) => r.data),
  uploadEpisodeVideo: (episodeId: number, file: File, onProgress?: (pct: number) => void) => {
    const data = new FormData();
    data.append("file", file);
    return api.post(`/v1/admin/episodes/${episodeId}/upload-video`, data, {
      headers: { "Content-Type": "multipart/form-data" },
      onUploadProgress: (e) => {
        if (e.total && onProgress) onProgress(Math.round((e.loaded / e.total) * 100));
      },
    }).then((r) => r.data);
  },

  // Subtitle (.vtt) upload. The endpoint upserts by (owner, language) so
  // re-uploading the same language replaces the previous file.
  uploadTitleSubtitle: (
    titleId: number,
    file: File,
    params: { language: string; kind?: "subtitle" | "cc" | "sdh" | "dubtitle"; forced?: boolean; label?: string },
  ) => {
    const data = new FormData();
    data.append("file", file);
    return api
      .post(`/v1/admin/titles/${titleId}/subtitles`, data, {
        headers: { "Content-Type": "multipart/form-data" },
        params,
      })
      .then((r) => r.data);
  },
  uploadEpisodeSubtitle: (
    episodeId: number,
    file: File,
    params: { language: string; kind?: "subtitle" | "cc" | "sdh" | "dubtitle"; forced?: boolean; label?: string },
  ) => {
    const data = new FormData();
    data.append("file", file);
    return api
      .post(`/v1/admin/episodes/${episodeId}/subtitles`, data, {
        headers: { "Content-Type": "multipart/form-data" },
        params,
      })
      .then((r) => r.data);
  },
  deleteSubtitle: (subtitleId: number) => api.delete(`/v1/admin/subtitles/${subtitleId}`),

  // Audit
  audit: (params: {
    entity_type?: string;
    entity_id?: number;
    actor_user_id?: number;
    page?: number;
    page_size?: number;
  } = {}) => api.get("/v1/admin/audit", { params }).then((r) => r.data),

  // Users
  users: (page = 1, page_size = 50) =>
    api.get("/v1/admin/users", { params: { page, page_size } }).then((r) => r.data),
  changeUserRole: (id: number, role: string) =>
    api.patch(`/v1/admin/users/${id}/role`, { role }).then((r) => r.data),
};
