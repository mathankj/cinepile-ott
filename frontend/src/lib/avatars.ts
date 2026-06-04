/**
 * Avatar registry — Netflix / Amazon Prime style illustrated character heads.
 *
 * Each avatar has a short stable `id` (stored on the Profile row) and resolves
 * to an SVG URL on demand. We use DiceBear's hosted SVG API (free, no key
 * needed); the seed is what makes each one look different. SVGs are tiny
 * (~3-5 KB) and the browser caches them after first load.
 *
 * Backwards compat: legacy profiles created before this registry may have
 * an emoji glyph in the `avatar` field (e.g. "👤"). `resolveAvatar` detects
 * that and returns null so the UI falls back to rendering the glyph.
 *
 * Why DiceBear over emoji:
 *  - Emoji rendering on Windows is sluggish at large sizes (was visibly
 *    lagging in the profile picker — the "appears late" UX the user flagged).
 *  - Different OSes render the same emoji very differently (Apple vs MS),
 *    which would make the picker look inconsistent across devices.
 *  - Illustrated portraits are what Netflix + Amazon Prime + Hotstar use.
 */

/** Avatar style — DiceBear 9.x `notionists-neutral` gives clean illustrated
 *  character heads with a neutral background that matches our dark theme. */
const DICEBEAR_STYLE = "notionists-neutral";

/** Background colour palette applied to every generated avatar. Picked to be
 *  warm + brand-consistent (not the default DiceBear pastels). */
const BG_PALETTE = "b6e3f4,c0aede,d1d4f9,ffd5dc,ffdfbf,c1f0d3,fae29d";

export type AvatarOption = {
  id: string;         // Stored on the Profile row
  label: string;      // What the picker shows under the tile
  url: string;        // Resolved SVG URL
};

/**
 * Curated set of 12 avatar identities. The DiceBear seed is just the id —
 * stable across users because we want everyone to see the same avatar when
 * they pick "panda". Ordered so the first few are most universally appealing
 * (kid-friendly + adult-friendly).
 */
const AVATARS: { id: string; label: string }[] = [
  { id: "default", label: "Default" },
  { id: "panda", label: "Panda" },
  { id: "fox", label: "Fox" },
  { id: "astronaut", label: "Astronaut" },
  { id: "ninja", label: "Ninja" },
  { id: "robot", label: "Robot" },
  { id: "wizard", label: "Wizard" },
  { id: "chef", label: "Chef" },
  { id: "warrior", label: "Warrior" },
  { id: "scientist", label: "Scientist" },
  { id: "kid", label: "Kid" },
  { id: "explorer", label: "Explorer" },
];

function buildUrl(seed: string): string {
  // DiceBear's hosted SVG API — params: seed (drives the character), backgroundColor.
  const params = new URLSearchParams({
    seed: `cinepile-${seed}`,
    backgroundColor: BG_PALETTE,
    radius: "12",
  });
  return `https://api.dicebear.com/9.x/${DICEBEAR_STYLE}/svg?${params.toString()}`;
}

export const AVATAR_OPTIONS: AvatarOption[] = AVATARS.map((a) => ({
  ...a,
  url: buildUrl(a.id),
}));

const AVATAR_INDEX = new Map(AVATAR_OPTIONS.map((a) => [a.id, a]));

/**
 * Resolve an avatar value from a Profile into a usable display.
 * - If the value matches a registered id → returns `{ url, label }`.
 * - If the value is an emoji glyph (legacy data) → returns `null` so the
 *   caller can render the glyph as text instead.
 */
export function resolveAvatar(value: string | null | undefined): AvatarOption | null {
  if (!value) return AVATAR_INDEX.get("default") ?? null;
  return AVATAR_INDEX.get(value) ?? null;
}

/** True when the stored avatar value is a single emoji glyph rather than an id.
 *  Cheap heuristic: ids are ASCII; emojis have code points outside ASCII. */
export function isLegacyEmoji(value: string | null | undefined): boolean {
  if (!value) return false;
  return /[\u{1F000}-\u{1FFFF}\u{2600}-\u{27BF}]/u.test(value);
}
