import { Link } from "react-router-dom";
import { Play, Info } from "lucide-react";
import type { TitleSummary } from "../../api/types";

/**
 * Hero billboard — the big top-of-home title card.
 * 85vh desktop, 60vh tablet, 50vh mobile.
 * Backdrop image + gradient fade-out to page bg.
 */
export function Billboard({ title }: { title: TitleSummary | null }) {
  if (!title) return null;
  return (
    <section className="relative h-[50vh] min-h-[400px] md:h-[60vh] lg:h-[85vh] w-full overflow-hidden">
      {title.backdrop_url || title.poster_url ? (
        <img
          src={title.backdrop_url || title.poster_url || ""}
          alt={title.title}
          className="absolute inset-0 h-full w-full object-cover"
        />
      ) : (
        <div className="absolute inset-0 bg-gradient-to-br from-[var(--color-bg-surface)] to-[var(--color-bg-elevated)]" />
      )}
      {/* Right-to-left content fade (so left side is readable) */}
      <div className="absolute inset-0 bg-gradient-to-r from-black via-black/50 to-transparent" />
      {/* Bottom-to-page fade */}
      <div className="absolute inset-x-0 bottom-0 h-32 hero-fade" />

      <div className="relative z-10 flex h-full flex-col justify-end pb-20 md:pb-32 px-4 md:px-8 lg:px-[60px] max-w-[700px]">
        <h1 className="text-[2.25rem] md:text-[3.5rem] font-extrabold leading-[1.1] text-white drop-shadow-lg">
          {title.title}
        </h1>
        {title.age_rating && (
          <div className="mt-3 inline-flex w-fit items-center gap-2 text-sm text-white/80">
            <span className="rounded border border-white/40 px-2 py-0.5 text-xs">
              {title.age_rating}
            </span>
            {title.release_year && <span>{title.release_year}</span>}
            {title.runtime_minutes && <span>{title.runtime_minutes} min</span>}
          </div>
        )}
        <div className="mt-6 flex flex-wrap gap-3">
          <Link
            to={`/watch/title/${title.id}`}
            className="inline-flex items-center gap-2 rounded bg-white px-7 py-3 text-base font-semibold text-black transition-colors duration-200 hover:bg-white/85"
          >
            <Play size={20} className="fill-current" /> Play
          </Link>
          <Link
            to={`/title/${title.id}`}
            className="inline-flex items-center gap-2 rounded bg-white/15 px-7 py-3 text-base font-semibold text-white backdrop-blur-sm transition-colors duration-200 hover:bg-white/25"
          >
            <Info size={20} /> More Info
          </Link>
        </div>
      </div>
    </section>
  );
}
