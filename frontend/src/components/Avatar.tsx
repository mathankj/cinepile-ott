/**
 * Avatar tile — colour-gradient background + centred Lucide icon.
 *
 * Renders instantly (no network), looks intentional, scales infinitely.
 * Use anywhere a profile's avatar appears: picker tiles, navbar trigger,
 * profile menu header, form modal.
 */
import { resolveAvatar } from "../lib/avatars";

type Size = "xs" | "sm" | "md" | "lg" | "xl";

const SIZE_PX: Record<Size, number> = {
  xs: 32,
  sm: 40,
  md: 56,
  lg: 120,
  xl: 160,
};

// Icon takes up ~50% of the tile so the gradient stays the dominant visual.
const ICON_FRACTION = 0.5;

export function Avatar({
  value,
  size = "md",
  className = "",
  alt,
}: {
  value: string | null | undefined;
  size?: Size;
  className?: string;
  alt?: string;
}) {
  const px = SIZE_PX[size];
  const opt = resolveAvatar(value);
  const Icon = opt.icon;
  const iconSize = Math.round(px * ICON_FRACTION);
  // Larger sizes deserve a softer rounded corner; xs/sm get a tighter radius
  // so the tile looks proportionally clean even at navbar dimensions.
  const radius = size === "xs" || size === "sm" ? "rounded-md" : "rounded-lg";

  return (
    <div
      className={`relative grid place-items-center bg-gradient-to-br ${opt.gradient} ${radius} shadow-sm ${className}`}
      style={{ width: px, height: px }}
      aria-label={alt ?? opt.label}
      role="img"
    >
      <Icon size={iconSize} className="text-white drop-shadow-sm" strokeWidth={2.25} />
    </div>
  );
}
