import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import type { TitleSummary } from "../../api/types";

/**
 * Single-title card — landscape 16:9.
 * Hover effects: scale 1.08 + sibling translate handled by parent flex gap.
 * Netflix uses cubic-bezier(0.5, 0, 0.1, 1) over 300ms.
 */
export function TitleCard({ title, progressPercent }: { title: TitleSummary; progressPercent?: number }) {
  return (
    <Link
      to={`/title/${title.id}`}
      className="group relative block flex-none overflow-hidden rounded-[4px]"
    >
      <motion.div
        whileHover={{ scale: 1.08, zIndex: 10 }}
        transition={{ duration: 0.3, ease: [0.5, 0, 0.1, 1] }}
        className="relative aspect-video w-full overflow-hidden rounded-[4px] bg-[var(--color-bg-elevated)]"
      >
        {title.backdrop_url || title.poster_url ? (
          <img
            src={title.backdrop_url || title.poster_url || ""}
            alt={title.title}
            loading="lazy"
            className="h-full w-full object-cover"
            onError={(e) => {
              // Fallback to placeholder gradient
              (e.target as HTMLImageElement).style.display = "none";
            }}
          />
        ) : (
          <div className="absolute inset-0 bg-gradient-to-br from-[var(--color-bg-surface)] to-[var(--color-bg-elevated)]" />
        )}
        {/* Bottom title strip — appears on hover */}
        <div className="absolute inset-x-0 bottom-0 flex items-end bg-gradient-to-t from-black/85 via-black/30 to-transparent p-2 opacity-0 transition-opacity duration-200 group-hover:opacity-100">
          <div className="min-w-0">
            <div className="truncate text-[13px] font-semibold text-white">{title.title}</div>
            <div className="text-[11px] text-white/70">
              {title.type === "series" ? "Series" : "Movie"}
              {title.release_year ? ` · ${title.release_year}` : ""}
              {title.age_rating ? ` · ${title.age_rating}` : ""}
            </div>
          </div>
        </div>
        {/* FREE badge */}
        {title.is_free && (
          <div className="absolute left-2 top-2 rounded bg-[var(--color-brand)] px-1.5 py-0.5 text-[10px] font-bold tracking-wider text-white">
            FREE
          </div>
        )}
        {/* Progress bar for Continue Watching */}
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
