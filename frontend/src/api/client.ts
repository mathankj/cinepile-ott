/**
 * Axios instance with auth + active-profile interceptors.
 *
 * - Attaches the access token from the auth store to every request.
 * - Attaches X-Profile-Id from the profile store so the backend scopes
 *   watchlist / progress / reactions / home rows to the active profile.
 * - On 401, tries to refresh once (rotates the refresh token), retries the
 *   original request, and on second 401 clears auth + redirects to /login.
 * - Calls /v1/* via the Vite proxy in dev, direct URL in prod.
 */
import axios, { type AxiosError, type AxiosRequestConfig } from "axios";
import { useAuthStore } from "../stores/auth";
import { useProfileStore } from "../stores/profile";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

export const api = axios.create({
  baseURL: BASE_URL,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Active-profile scoping — its own interceptor, deliberately separate from the
// auth/refresh logic above. The backend verifies ownership server-side and
// silently ignores ids that don't belong to the authenticated user, so a stale
// localStorage value can never scope into someone else's data.
api.interceptors.request.use((config) => {
  const profile = useProfileStore.getState().active;
  if (profile) config.headers["X-Profile-Id"] = String(profile.id);
  return config;
});

// Refresh-on-401 with a single-flight lock so concurrent 401s don't all refresh.
let refreshPromise: Promise<string | null> | null = null;

async function refreshOnce(): Promise<string | null> {
  const store = useAuthStore.getState();
  const refresh = store.refreshToken;
  if (!refresh) return null;
  try {
    const r = await axios.post<{
      access_token: string;
      refresh_token: string;
      expires_at: string;
    }>(`${BASE_URL}/v1/auth/refresh`, { refresh_token: refresh });
    store.setTokens(r.data.access_token, r.data.refresh_token);
    return r.data.access_token;
  } catch {
    store.clear();
    return null;
  }
}

api.interceptors.response.use(
  (r) => r,
  async (error: AxiosError) => {
    const original = error.config as AxiosRequestConfig & { _retried?: boolean };
    const status = error.response?.status;

    if (status === 401 && !original._retried) {
      original._retried = true;
      if (!refreshPromise) refreshPromise = refreshOnce();
      const newToken = await refreshPromise;
      refreshPromise = null;
      if (newToken) {
        original.headers = { ...(original.headers ?? {}), Authorization: `Bearer ${newToken}` };
        return api(original);
      }
      // Refresh failed — let the auth-aware routes redirect to /login.
    }
    return Promise.reject(error);
  }
);

/** Convenience: extract a clean error message from our backend's error envelope.
 *
 * Handles three shapes:
 *   1. Our explicit error envelope:   { detail: { error: { message } } }
 *   2. FastAPI validation 422:        { detail: [{loc, msg, type}] }
 *      → pick the first user-friendly msg
 *   3. Anything else                  → axios message → fallback
 */
export function apiErrorMessage(err: unknown, fallback = "Something went wrong"): string {
  if (axios.isAxiosError(err)) {
    const data = err.response?.data;
    // Shape 1: our error envelope
    const enveloped = (data as { detail?: { error?: { message?: string } } } | undefined)?.detail
      ?.error?.message;
    if (enveloped) return enveloped;
    // Shape 2: FastAPI 422 — array of validation errors
    const detail = (data as { detail?: unknown } | undefined)?.detail;
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0] as { msg?: string; loc?: unknown[] };
      if (first.msg) {
        const field = Array.isArray(first.loc) ? String(first.loc.at(-1) ?? "") : "";
        // "value_error, value is not a valid email address" → "Please enter a valid email address."
        const friendly = first.msg.replace(/^value_error,?\s*/i, "").replace(/^Value error,?\s*/i, "");
        return field ? `${field}: ${friendly}` : friendly;
      }
    }
    return err.message ?? fallback;
  }
  return fallback;
}
