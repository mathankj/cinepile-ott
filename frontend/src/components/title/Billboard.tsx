import { useState } from "react";
import { Link } from "react-router-dom";
import { Play, Info } from "lucide-react";
import type { TitleSummary } from "../../api/types";

/**
 * Hero billboard — the big top-of-home title card.
 * 85vh desktop, 60vh tablet, 50vh mobile.
 * Backdrop image + gradient fade-out to page bg.
 *
 * When no backdrop is available (or it fails to load), we render a
 * brand-tinted gradient with the title prominently displayed — never
 * leave the hero as a flat dark void.
 */
export function Billboard({ title }: { title: TitleSummary | null }) {
  const [imgFailed, setImgFailed] = useState(false);
  if (!title) return null;
  const imgUrl = title.backdrop_url || title.poster_url;
  const showImage = imgUrl && !imgFailed;

  // Deterministic hue from title for the no-image fallback
  let hash = 0;
  for (let i = 0; i < title.title.length; i++) hash = (hash * 31 + title.title.charCodeAt(i)) | 0;
  const hue = Math.abs(hash) % 360;

  return (
    <section className="relative h-[50vh] min-h-[400px] md:h-[60vh] lg:h-[85vh] w-full overflow-hidden">
      {showImage ? (
        <img
          src={imgUrl}
          alt={title.title}
          className="absolute inset-0 h-full w-full object-cover"
          onError={() => setImgFailed(true)}
        />
      ) : (
        <div
          className="absolute inset-0"
          style={{
            background: `radial-gradient(120% 80% at 30% 50%, hsla(${hue}, 60%, 30%, 0.7) 0%, hsla(${(hue + 60) % 360}, 40%, 12%, 0.95) 60%, #141414 100%)`,
          }}
        />
      )}
      {/* Left-to-right scrim so left-side text stays readable */}
      <div className="absolute inset-0 bg-gradient-to-r from-black/80 via-black/40 to-transparent" />
      {/* Bottom-to-page fade */}
      <div className="absolute inset-x-0 bottom-0 h-32 hero-fade" />

      <div className="relative z-10 flex h-full flex-col justify-end pb-20 md:pb-32 px-4 md:px-8 lg:px-[60px] max-w-[700px]">
        <h1 className="text-[2.25rem] md:text-[3.5rem] font-extrabold leading-[1.1] text-white drop-shadow-lg">
          {title.title}
        </h1>
        <div className="mt-3 flex flex-wrap items-center gap-3 text-sm text-white/80">
          {title.age_rating && (
            <span className="rounded border border-white/40 px-2 py-0.5 text-xs">
              {title.age_rating}
            </span>
          )}
          {title.release_year && <span>{title.release_year}</span>}
          {title.runtime_minutes && <span>{title.runtime_minutes} min</span>}
          <span className="rounded bg-white/10 px-2 py-0.5 text-xs uppercase tracking-wider">
            {title.type}
          </span>
          {title.is_free && (
            <span className="rounded bg-[var(--color-brand)] px-2 py-0.5 text-xs font-bold tracking-wider text-white">
              FREE
            </span>
          )}
        </div>
        <div className="mt-6 flex flex-wrap gap-3">
          <Link
            to={title.type === "series" ? `/title/${title.id}` : `/watch/title/${title.id}`}
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
