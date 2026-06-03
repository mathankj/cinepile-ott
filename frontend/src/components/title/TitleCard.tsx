import { useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { useQueryClient } from "@tanstack/react-query";
import { catalog } from "../../api";
import type { TitleSummary } from "../../api/types";

/**
 * Single-title card — landscape 16:9.
 *
 * Lazy/perf optimisations baked in:
 * - `loading="lazy"` on the img so off-screen rows don't block paint.
 * - Hover prefetches `catalog.detail(title.id)` into the TanStack Query cache
 *   so the TitleDetail page renders instantly on click (vs. waiting for a
 *   network round-trip after navigation).
 * - Image error fallback: deterministic gradient + title text so the row
 *   still feels alive when art is missing.
 *
 * Visual conventions from the Netflix research:
 *  scale 1.08, 300ms, cubic-bezier(0.5, 0, 0.1, 1)
 *  rounded-[4px], no drop shadow, no overflow blur
 */
export function TitleCard({
  title,
  progressPercent,
}: {
  title: TitleSummary;
  progressPercent?: number;
}) {
  const qc = useQueryClient();
  const imgUrl = title.backdrop_url || title.poster_url;
  const [imgFailed, setImgFailed] = useState(false);
  const showImage = imgUrl && !imgFailed;

  // Prefetch detail on hover — runs at most once per card per session because
  // TanStack Query dedupes via the queryKey.
  function prefetch() {
    qc.prefetchQuery({
      queryKey: ["title", title.id],
      queryFn: () => catalog.detail(title.id),
      staleTime: 60_000,
    });
  }

  return (
    <Link
      to={`/title/${title.id}`}
      onMouseEnter={prefetch}
      onFocus={prefetch}
      className="group relative block flex-none overflow-hidden rounded-[4px]"
    >
      <motion.div
        whileHover={{ scale: 1.08, zIndex: 10 }}
        transition={{ duration: 0.3, ease: [0.5, 0, 0.1, 1] }}
        className="relative aspect-video w-full overflow-hidden rounded-[4px] bg-[var(--color-bg-elevated)]"
      >
        {showImage ? (
          <img
            src={imgUrl}
            alt={title.title}
            loading="lazy"
            decoding="async"
            className="h-full w-full object-cover"
            onError={() => setImgFailed(true)}
          />
        ) : (
          <FallbackTile title={title.title} />
        )}

        {/* Always-visible bottom title strip */}
        <div className="absolute inset-x-0 bottom-0 flex items-end bg-gradient-to-t from-black/85 via-black/30 to-transparent p-2 pt-6">
          <div className="min-w-0">
            <div className="truncate text-[13px] font-semibold leading-tight text-white">
              {title.title}
            </div>
            <div className="mt-0.5 text-[11px] text-white/70">
              {title.type === "series" ? "Series" : "Movie"}
              {title.release_year ? ` · ${title.release_year}` : ""}
              {title.age_rating ? ` · ${title.age_rating}` : ""}
            </div>
          </div>
        </div>

        {title.is_free && (
          <div className="absolute left-2 top-2 rounded bg-[var(--color-brand)] px-1.5 py-0.5 text-[10px] font-bold tracking-wider text-white shadow-lg">
            FREE
          </div>
        )}

        {typeof progressPercent === "number" && progressPercent > 0 && (
          <div className="absolute inset-x-0 bottom-0 h-1 bg-white/20">
            <div
              className="h-full bg-[var(--color-brand)]"
              style={{ width: `${Math.min(100, Math.max(0, progressPercent))}%` }}
            />
          </div>
        )}
      </motion.div>
    </Link>
  );
}

function FallbackTile({ title }: { title: string }) {
  let hash = 0;
  for (let i = 0; i < title.length; i++) hash = (hash * 31 + title.charCodeAt(i)) | 0;
  const hue = Math.abs(hash) % 360;
  const grad = `linear-gradient(135deg, hsl(${hue}, 35%, 22%), hsl(${(hue + 40) % 360}, 28%, 12%))`;
  return (
    <div className="absolute inset-0 flex items-center justify-center p-3" style={{ background: grad }}>
      <div className="text-center text-white">
        <div className="text-[15px] font-bold leading-tight drop-shadow">{title}</div>
      </div>
    </div>
  );
}
