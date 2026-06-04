/**
 * Avatar tile — renders an illustrated character SVG when the value is a
 * registered avatar id, or falls back to the legacy emoji glyph + a subtle
 * skeleton shimmer while the SVG loads.
 *
 * Use anywhere a profile's avatar appears: the picker tiles, the navbar
 * dropdown trigger, the profile menu header.
 */
import { useState } from "react";
import { resolveAvatar, isLegacyEmoji } from "../lib/avatars";

type Size = "xs" | "sm" | "md" | "lg" | "xl";

const SIZE_PX: Record<Size, number> = {
  xs: 28,
  sm: 36,
  md: 56,
  lg: 120,
  xl: 160,
};

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
  const [loaded, setLoaded] = useState(false);

  // Legacy emoji path — render the glyph in a coloured tile so it still
  // looks branded. No async load → no shimmer needed.
  if (!opt && isLegacyEmoji(value)) {
    return (
      <div
        className={`grid place-items-center rounded-md bg-gradient-to-br from-[#1a1a1a] to-[#2a2a2a] ${className}`}
        style={{ width: px, height: px }}
        aria-label={alt ?? "Profile avatar"}
      >
        <span style={{ fontSize: px * 0.6, lineHeight: 1 }}>{value}</span>
      </div>
    );
  }

  // Modern path — DiceBear SVG with shimmer placeholder while it loads.
  // The placeholder uses the same dimensions to avoid layout shift.
  const url = opt?.url;
  return (
    <div
      className={`relative overflow-hidden rounded-md bg-gradient-to-br from-[#1a1a1a] to-[#2a2a2a] ${className}`}
      style={{ width: px, height: px }}
      aria-label={alt ?? opt?.label ?? "Profile avatar"}
    >
      {!loaded && <div className="skeleton-shimmer absolute inset-0" />}
      {url && (
        <img
          src={url}
          alt={alt ?? opt?.label ?? ""}
          width={px}
          height={px}
          loading="eager"
          decoding="async"
          onLoad={() => setLoaded(true)}
          // Inline `style` rather than Tailwind so the SVG sits at exactly
          // the requested pixel size regardless of viewport (the SVG itself
          // is responsive and would otherwise inherit 100%).
          style={{
            width: px,
            height: px,
            opacity: loaded ? 1 : 0,
            transition: "opacity 180ms ease-out",
          }}
        />
      )}
    </div>
  );
}
