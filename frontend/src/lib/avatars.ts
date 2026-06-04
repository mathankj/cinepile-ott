/**
 * Avatar registry — bold colour-gradient tiles with a centred Lucide icon.
 *
 * Why this design over network-fetched cartoon faces:
 *  - Instant render (no SVG over the wire, no DiceBear API dependency)
 *  - Scales infinitely (icon is an SVG; gradient is CSS)
 *  - Looks intentional + modern (Amazon Prime, Hotstar use solid-colour tiles
 *    with iconography; Netflix uses character portraits we don't have IP for)
 *  - Each tile has a distinct identity via colour + icon combo
 *
 * Each avatar has:
 *  - id: short stable string stored on the Profile row
 *  - label: human-readable name shown in the picker
 *  - icon: a Lucide icon component
 *  - gradient: a Tailwind CSS gradient class for the background
 *
 * Backwards compat:
 *  - Legacy emoji avatars (👤 etc.) and unknown ids fall through to the
 *    "default" tile rather than rendering broken.
 */
import type { LucideIcon } from "lucide-react";
import {
  Bot,
  ChefHat,
  Compass,
  Crown,
  Flame,
  FlaskConical,
  Gamepad2,
  Heart,
  Rocket,
  Shield,
  Smile,
  Sparkles,
  Star,
  Sword,
  User,
} from "lucide-react";

export type AvatarOption = {
  id: string;
  label: string;
  icon: LucideIcon;
  /** Tailwind gradient classes — applied to the tile background */
  gradient: string;
};

/**
 * Curated 12 avatars. Colour palette is hand-picked for variety + vibrance,
 * not auto-generated. Each id is the seed key written to the database; once
 * shipped to users, NEVER rename or you'll orphan their profile selection.
 */
export const AVATAR_OPTIONS: AvatarOption[] = [
  { id: "default",   label: "Default",   icon: User,         gradient: "from-indigo-500 to-purple-700" },
  { id: "panda",     label: "Panda",     icon: Heart,        gradient: "from-pink-500 to-rose-700" },
  { id: "fox",       label: "Fox",       icon: Flame,        gradient: "from-orange-500 to-red-700" },
  { id: "astronaut", label: "Astronaut", icon: Rocket,       gradient: "from-slate-700 to-blue-900" },
  { id: "ninja",     label: "Ninja",     icon: Sword,        gradient: "from-zinc-800 to-black" },
  { id: "robot",     label: "Robot",     icon: Bot,          gradient: "from-cyan-500 to-teal-700" },
  { id: "wizard",    label: "Wizard",    icon: Sparkles,     gradient: "from-violet-500 to-purple-800" },
  { id: "chef",      label: "Chef",      icon: ChefHat,      gradient: "from-amber-400 to-orange-600" },
  { id: "warrior",   label: "Warrior",   icon: Shield,       gradient: "from-red-600 to-rose-900" },
  { id: "scientist", label: "Scientist", icon: FlaskConical, gradient: "from-emerald-500 to-green-800" },
  { id: "kid",       label: "Kid",       icon: Smile,        gradient: "from-yellow-400 to-amber-600" },
  { id: "explorer",  label: "Explorer",  icon: Compass,      gradient: "from-teal-500 to-emerald-800" },
  { id: "gamer",     label: "Gamer",     icon: Gamepad2,     gradient: "from-fuchsia-500 to-pink-700" },
  { id: "vip",       label: "VIP",       icon: Crown,        gradient: "from-yellow-500 to-amber-700" },
  { id: "star",      label: "Star",      icon: Star,         gradient: "from-sky-400 to-blue-700" },
];

const AVATAR_INDEX = new Map(AVATAR_OPTIONS.map((a) => [a.id, a]));

/**
 * Resolve a stored avatar value to its render config. Unknown ids and legacy
 * emoji glyphs both fall through to "default" so nothing ever renders broken.
 */
export function resolveAvatar(value: string | null | undefined): AvatarOption {
  if (!value) return AVATAR_INDEX.get("default")!;
  return AVATAR_INDEX.get(value) ?? AVATAR_INDEX.get("default")!;
}
