/**
 * Active-profile store. Persists the currently selected profile in localStorage
 * so the picker only fires once per device. Cleared on logout (via auth store).
 *
 * The active profile is REAL scoping, not cosmetic: an axios request
 * interceptor in api/client.ts sends `X-Profile-Id: <id>` on every call, and
 * the backend scopes watchlist / progress / reactions / home rows to it (and
 * enforces U-rated-only playback for kid profiles). The header is verified
 * server-side against the logged-in user, so a stale persisted value is
 * harmlessly ignored rather than leaking another account's data.
 */
import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { Profile } from "../api/types";

type ProfileState = {
  active: Profile | null;
  setActive: (p: Profile | null) => void;
  clear: () => void;
};

export const useProfileStore = create<ProfileState>()(
  persist(
    (set) => ({
      active: null,
      setActive: (p) => set({ active: p }),
      clear: () => set({ active: null }),
    }),
    { name: "anjaneya-profile" },
  ),
);
