import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { Play } from "lucide-react";
import { catalog } from "../api";

/**
 * Season detail — list of episodes for a season.
 * Scheduled episodes are shown but with "Coming on …" instead of a Play link.
 */
export default function SeasonPage() {
  const { titleId, seasonNumber } = useParams();
  const tid = Number(titleId);
  const sn = Number(seasonNumber);

  const { data: season } = useQuery({
    queryKey: ["season", tid, sn],
    queryFn: () => catalog.season(tid, sn),
    enabled: Number.isFinite(tid) && Number.isFinite(sn),
  });

  const { data: title } = useQuery({
    queryKey: ["title", tid],
    queryFn: () => catalog.detail(tid),
    enabled: Number.isFinite(tid),
  });

  if (!season || !title) return <div className="p-8 text-white/60">Loading…</div>;

  return (
    <div className="px-4 md:px-8 lg:px-[60px] py-12">
      <Link to={`/title/${tid}`} className="text-sm text-white/60 hover:text-white">
        ← {title.title}
      </Link>
      <h1 className="mt-2 text-[2rem] font-bold">
        {season.name || `Season ${season.season_number}`}
      </h1>
      {season.synopsis && <p className="mt-2 max-w-[640px] text-white/70">{season.synopsis}</p>}

      <div className="mt-8 grid gap-4">
        {season.episodes.map((ep) => {
          const isPlayable = ep.status === "published";
          return (
            <article
              key={ep.id}
              className="flex flex-col gap-4 rounded border border-white/10 bg-[var(--color-bg-elevated)] p-4 md:flex-row md:items-center"
            >
              <div className="flex-none aspect-video w-full md:w-[200px] rounded overflow-hidden bg-black">
                {/* Episode thumbnail — fall back to series backdrop */}
                {title.backdrop_url ? (
                  <img src={title.backdrop_url} alt={ep.name} className="h-full w-full object-cover" />
                ) : (
                  <div className="h-full w-full bg-gradient-to-br from-[var(--color-bg-surface)] to-[var(--color-bg-elevated)]" />
                )}
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm text-white/50">Ep {ep.episode_number}</span>
                  {ep.is_free && (
                    <span className="rounded bg-[var(--color-brand)] px-1.5 py-0.5 text-[10px] font-bold tracking-wider text-white">
                      FREE
                    </span>
                  )}
                  {!isPlayable && (
                    <span className="rounded bg-white/15 px-2 py-0.5 text-[11px] uppercase tracking-wider text-white/80">
                      {ep.status === "scheduled" ? "Coming soon" : ep.status}
                    </span>
                  )}
                </div>
                <h3 className="mt-1 text-lg font-semibold">{ep.name}</h3>
                {ep.synopsis && (
                  <p className="mt-1 text-sm text-white/70 line-clamp-2">{ep.synopsis}</p>
                )}
                {ep.runtime_seconds && (
                  <div className="mt-1 text-xs text-white/50">
                    {Math.round(ep.runtime_seconds / 60)} min
                  </div>
                )}
              </div>
              <div className="flex-none">
                {isPlayable ? (
                  <Link
                    to={`/watch/episode/${ep.id}`}
                    className="inline-flex items-center gap-2 rounded bg-white px-5 py-2.5 font-semibold text-black hover:bg-white/85"
                  >
                    <Play size={16} className="fill-current" /> Play
                  </Link>
                ) : (
                  <button
                    type="button"
                    disabled
                    className="inline-flex items-center gap-2 rounded bg-white/10 px-5 py-2.5 font-semibold text-white/40"
                  >
                    Coming soon
                  </button>
                )}
              </div>
            </article>
          );
        })}
      </div>
    </div>
  );
}
