/**
 * Axios instance with auth interceptor.
 *
 * - Attaches the access token from the auth store to every request.
 * - On 401, tries to refresh once (rotates the refresh token), retries the
 *   original request, and on second 401 clears auth + redirects to /login.
 * - Calls /v1/* via the Vite proxy in dev, direct URL in prod.
 */
import axios, { type AxiosError, type AxiosRequestConfig } from "axios";
import { useAuthStore } from "../stores/auth";

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

/** Convenience: extract a clean error message from our backend's error envelope. */
export function apiErrorMessage(err: unknown, fallback = "Something went wrong"): string {
  if (axios.isAxiosError(err)) {
    const body = err.response?.data as { detail?: { error?: { message?: string } } } | undefined;
    return body?.detail?.error?.message ?? err.message ?? fallback;
  }
  return fallback;
}
