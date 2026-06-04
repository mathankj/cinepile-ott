import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Play, Plus, Info, Check } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { catalog, me } from "../../api";
import type { TitleSummary } from "../../api/types";
import { useAuthStore } from "../../stores/auth";

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
 *
 * Hover reveal (Netflix mini-card pattern):
 *  After 400ms hover, fade in an action overlay with Play / + List / More-info
 *  icon buttons. Quick-hover stays fast (no flash); committed hover gets the
 *  full preview. Touch devices skip the reveal — `@media (hover:none)`.
 */
export function TitleCard({
  title,
  progressPercent,
}: {
  title: TitleSummary;
  progressPercent?: number;
}) {
  const qc = useQueryClient();
  const nav = useNavigate();
  const isLoggedIn = useAuthStore((s) => !!s.accessToken);
  const imgUrl = title.backdrop_url || title.poster_url;
  const [imgFailed, setImgFailed] = useState(false);
  const showImage = imgUrl && !imgFailed;

  // Watchlist state — only fetched when the user is logged in. The card uses
  // it to flip the "+" icon to a "✓" when the title is already on the list.
  const watchlistQ = useQuery({
    queryKey: ["watchlist"],
    queryFn: () => me.listWatchlist(),
    enabled: isLoggedIn,
    staleTime: 30_000,
  });
  const onList =
    !!watchlistQ.data?.items.some((w) => w.title.id === title.id);

  const addToList = useMutation({
    mutationFn: () => me.addToList(title.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["watchlist"] }),
  });
  const removeFromList = useMutation({
    mutationFn: () => me.removeFromList(title.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["watchlist"] }),
  });

  // Prefetch detail on hover — runs at most once per card per session because
  // TanStack Query dedupes via the queryKey.
  function prefetch() {
    qc.prefetchQuery({
      queryKey: ["title", title.id],
      queryFn: () => catalog.detail(title.id),
      staleTime: 60_000,
    });
  }

  // Hover-overlay button handlers. Each one stops propagation so the outer
  // Link's navigation doesn't fire on the same click.
  function onPlayClick(e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    // Series go to detail (where the user picks an episode); movies go straight
    // to /watch. /watch is auth-protected so anonymous → /login redirect.
    nav(title.type === "series" ? `/title/${title.id}` : `/watch/title/${title.id}`);
  }
  function onListClick(e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    if (!isLoggedIn) {
      nav("/login", { state: { from: `/title/${title.id}` } });
      return;
    }
    if (onList) removeFromList.mutate();
    else addToList.mutate();
  }
  function onInfoClick(e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    nav(`/title/${title.id}`);
  }

  return (
    <Link
      to={`/title/${title.id}`}
      onMouseEnter={prefetch}
      onFocus={prefetch}
      className="group/card relative block flex-none rounded-[4px] focus-visible:outline focus-visible:outline-2 focus-visible:outline-white/60"
    >
      <motion.div
        whileHover={{ scale: 1.08, zIndex: 10 }}
        transition={{ duration: 0.3, ease: [0.5, 0, 0.1, 1] }}
        className="relative aspect-video w-full overflow-hidden rounded-[4px] bg-[var(--color-bg-elevated)] shadow-[0_0_0_0_rgba(0,0,0,0)] group-hover/card:shadow-[0_10px_30px_-10px_rgba(0,0,0,0.8)] transition-shadow duration-300"
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

        {/* Idle bottom title strip — hides on hover so the reveal overlay can take over. */}
        <div className="absolute inset-x-0 bottom-0 flex items-end bg-gradient-to-t from-black/85 via-black/30 to-transparent p-2 pt-6 opacity-100 transition-opacity duration-200 group-hover/card:opacity-0">
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

        {/* Hover reveal — Netflix mini-card. Fades in with a slight delay so
            quick mouse-overs (scrolling past the row) don't flash. Also
            triggers on keyboard focus inside the card (group-focus-within)
            so Tab users can reach the actions. Suppressed on touch via
            `@media (hover: none)` — the .hover-reveal class is wrapped in
            a hover-only block in index.css. */}
        <div
          className="hover-reveal pointer-events-none absolute inset-0 flex flex-col justify-between bg-gradient-to-t from-black/95 via-black/60 to-transparent p-3 opacity-0 transition-opacity duration-200 ease-out group-hover/card:pointer-events-auto group-hover/card:opacity-100 group-hover/card:delay-[400ms] group-focus-within/card:pointer-events-auto group-focus-within/card:opacity-100"
        >
          <div className="flex justify-end">
            {title.is_free && (
              <span className="rounded bg-[var(--color-brand)] px-1.5 py-0.5 text-[10px] font-bold tracking-wider text-white">
                FREE
              </span>
            )}
          </div>
          <div>
            <div className="line-clamp-1 text-[14px] font-semibold text-white">{title.title}</div>
            <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] text-white/80">
              {title.age_rating && (
                <span className="rounded border border-white/40 px-1 py-0.5">{title.age_rating}</span>
              )}
              {title.release_year && <span>{title.release_year}</span>}
              {title.runtime_minutes && <span>{title.runtime_minutes}m</span>}
              <span className="uppercase tracking-wider">{title.type}</span>
            </div>
            <div className="mt-2 flex items-center gap-1.5">
              <CardActionButton ariaLabel="Play" filled onClick={onPlayClick}>
                <Play size={14} className="fill-current" />
              </CardActionButton>
              <CardActionButton
                ariaLabel={onList ? "Remove from my list" : "Add to my list"}
                onClick={onListClick}
                pending={addToList.isPending || removeFromList.isPending}
              >
                {onList ? <Check size={14} /> : <Plus size={14} />}
              </CardActionButton>
              <CardActionButton ariaLabel="More info" onClick={onInfoClick}>
                <Info size={14} />
              </CardActionButton>
            </div>
          </div>
        </div>

        {/* Idle FREE badge — top-left when not hovering. Mirrors the badge inside
            the hover reveal so we never have both visible at once. */}
        {title.is_free && (
          <div className="absolute left-2 top-2 rounded bg-[var(--color-brand)] px-1.5 py-0.5 text-[10px] font-bold tracking-wider text-white shadow-lg transition-opacity duration-200 group-hover/card:opacity-0">
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

/**
 * Round icon button used inside the hover reveal. Filled = primary CTA (Play).
 * Stops link propagation so clicking Play doesn't bubble up into the card's
 * outer <Link> twice.
 */
function CardActionButton({
  children,
  filled = false,
  ariaLabel,
  onClick,
  pending = false,
}: {
  children: React.ReactNode;
  filled?: boolean;
  ariaLabel: string;
  onClick: (e: React.MouseEvent) => void;
  pending?: boolean;
}) {
  return (
    <button
      type="button"
      aria-label={ariaLabel}
      onClick={onClick}
      disabled={pending}
      className={`grid h-7 w-7 place-items-center rounded-full transition-colors disabled:opacity-50 ${
        filled
          ? "bg-white text-black hover:bg-white/85"
          : "border border-white/60 text-white hover:border-white hover:bg-white/10"
      }`}
    >
      {children}
    </button>
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
