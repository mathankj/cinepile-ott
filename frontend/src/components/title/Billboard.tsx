import { useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Play, Info } from "lucide-react";
import { useTranslation } from "react-i18next";
import type { TitleSummary } from "../../api/types";

/**
 * Hero billboard — the big top-of-home title card.
 * 85vh desktop, 60vh tablet, 50vh mobile.
 * Backdrop image + gradient fade-out to page bg.
 *
 * When no backdrop is available (or it fails to load), we render a
 * brand-tinted gradient with the title prominently displayed — never
 * leave the hero as a flat dark void.
 *
 * Entrance: backdrop crossfades in over 600ms; foreground copy slides up +
 * fades in with a small stagger. Subsequent renders (e.g. hero title swap
 * on data refresh) are keyed by id so the entrance plays again.
 */
export function Billboard({ title }: { title: TitleSummary | null }) {
  const [imgFailed, setImgFailed] = useState(false);
  const { t } = useTranslation();
  if (!title) return null;
  const imgUrl = title.backdrop_url || title.poster_url;
  const showImage = imgUrl && !imgFailed;

  // Deterministic hue from title for the no-image fallback
  let hash = 0;
  for (let i = 0; i < title.title.length; i++) hash = (hash * 31 + title.title.charCodeAt(i)) | 0;
  const hue = Math.abs(hash) % 360;

  // Stagger the foreground text + CTAs so the eye lands on the title first.
  const fgT = (delay: number) => ({
    initial: { opacity: 0, y: 16 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: 0.45, delay, ease: [0.5, 0, 0.1, 1] as [number, number, number, number] },
  });

  // Warm the Watch page's JS chunk (player + hls.js) on hover/focus of the
  // Play CTA, so clicking it starts playback immediately instead of first
  // downloading ~500 KB. The browser dedupes repeat dynamic imports.
  function prefetchWatchChunk() {
    void import("../../pages/Watch");
  }

  return (
    <section
      key={title.id}
      className="relative h-[50vh] min-h-[400px] md:h-[60vh] lg:h-[85vh] w-full overflow-hidden"
    >
      <motion.div
        initial={{ opacity: 0, scale: 1.04 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.7, ease: "easeOut" }}
        className="absolute inset-0"
      >
        {showImage ? (
          <img
            src={imgUrl}
            alt={title.title}
            // This is the page's LCP element — tell the browser to fetch it
            // ahead of other images and decode it off the main thread.
            fetchPriority="high"
            decoding="async"
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
      </motion.div>
      {/* Left-to-right scrim so left-side text stays readable */}
      <div className="absolute inset-0 bg-gradient-to-r from-black/80 via-black/40 to-transparent" />
      {/* Bottom-to-page fade */}
      <div className="absolute inset-x-0 bottom-0 h-32 hero-fade" />

      <div className="relative z-10 flex h-full flex-col justify-end pb-20 md:pb-32 px-4 md:px-8 lg:px-[60px] max-w-[700px]">
        <motion.h1
          {...fgT(0.1)}
          className="text-[2.25rem] md:text-[3.5rem] font-extrabold leading-[1.1] text-white drop-shadow-lg"
        >
          {title.title}
        </motion.h1>
        <motion.div
          {...fgT(0.2)}
          className="mt-3 flex flex-wrap items-center gap-3 text-sm text-white/80"
        >
          {title.age_rating && (
            <span className="rounded border border-white/40 px-2 py-0.5 text-xs">
              {title.age_rating}
            </span>
          )}
          {title.release_year && <span>{title.release_year}</span>}
          {title.runtime_minutes && <span>{t("common.minutes", { minutes: title.runtime_minutes })}</span>}
          <span className="rounded bg-white/10 px-2 py-0.5 text-xs uppercase tracking-wider">
            {title.type === "series" ? t("common.series") : t("common.movie")}
          </span>
          {title.is_free && (
            <span className="rounded bg-[var(--color-brand)] px-2 py-0.5 text-xs font-bold tracking-wider text-white">
              {t("billboard.free")}
            </span>
          )}
        </motion.div>
        <motion.div {...fgT(0.32)} className="mt-6 flex flex-wrap gap-3">
          <Link
            to={title.type === "series" ? `/title/${title.id}` : `/watch/title/${title.id}`}
            onMouseEnter={prefetchWatchChunk}
            onFocus={prefetchWatchChunk}
            className="group/btn inline-flex items-center gap-2 rounded bg-white px-7 py-3 text-base font-semibold text-black transition-all duration-200 hover:bg-white/85 active:scale-[0.98]"
          >
            <Play size={20} className="fill-current transition-transform duration-200 group-hover/btn:scale-110" /> {t("billboard.play")}
          </Link>
          <Link
            to={`/title/${title.id}`}
            className="group/btn inline-flex items-center gap-2 rounded bg-white/15 px-7 py-3 text-base font-semibold text-white backdrop-blur-sm transition-all duration-200 hover:bg-white/25 active:scale-[0.98]"
          >
            <Info size={20} className="transition-transform duration-200 group-hover/btn:scale-110" /> {t("billboard.more_info")}
          </Link>
        </motion.div>
      </div>
    </section>
  );
}
