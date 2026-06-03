/**
 * Active-profile store. Persists the currently selected profile in localStorage
 * so the picker only fires once per device. Cleared on logout (via auth store).
 *
 * NB: the backend doesn't yet scope reactions / continue-watching by profile —
 * that's a follow-up. Today the active profile is mostly cosmetic (drives the
 * avatar shown in the navbar). When backend scoping lands, every API call
 * will get a `?profile_id=<id>` query param automatically via the axios
 * interceptor.
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
