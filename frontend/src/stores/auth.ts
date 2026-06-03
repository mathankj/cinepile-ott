/**
 * Auth store — Zustand with localStorage persistence.
 *
 * Holds: access token, refresh token, and a cached user profile.
 * The access token is short-lived (15 min); the refresh token is rotated on
 * every refresh call by the API client.
 */
import { create } from "zustand";
import { persist } from "zustand/middleware";

export type AuthUser = {
  id: number;
  email: string;
  full_name: string | null;
  role: "user" | "viewer" | "content_manager" | "admin";
  is_active: boolean;
  created_at: string;
};

type AuthState = {
  accessToken: string | null;
  refreshToken: string | null;
  user: AuthUser | null;
  setTokens: (access: string, refresh: string) => void;
  setUser: (u: AuthUser | null) => void;
  setAuth: (access: string, refresh: string, u: AuthUser) => void;
  clear: () => void;
  isLoggedIn: () => boolean;
  hasRole: (...roles: AuthUser["role"][]) => boolean;
};

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      accessToken: null,
      refreshToken: null,
      user: null,
      setTokens: (access, refresh) => set({ accessToken: access, refreshToken: refresh }),
      setUser: (u) => set({ user: u }),
      setAuth: (access, refresh, u) =>
        set({ accessToken: access, refreshToken: refresh, user: u }),
      clear: () => set({ accessToken: null, refreshToken: null, user: null }),
      isLoggedIn: () => !!get().accessToken,
      hasRole: (...roles) => {
        const r = get().user?.role;
        return r ? roles.includes(r) : false;
      },
    }),
    { name: "anjaneya-auth" }
  )
);
