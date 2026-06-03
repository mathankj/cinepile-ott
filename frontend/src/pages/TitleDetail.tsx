import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { Play, Plus, Check, ThumbsUp, ThumbsDown, Heart } from "lucide-react";
import { catalog, me } from "../api";
import { useAuthStore } from "../stores/auth";

export default function TitleDetail() {
  const { id } = useParams();
  const titleId = Number(id);
  const qc = useQueryClient();
  const isLoggedIn = useAuthStore((s) => s.isLoggedIn());

  const { data: title, isLoading } = useQuery({
    queryKey: ["title", titleId],
    queryFn: () => catalog.detail(titleId),
    enabled: Number.isFinite(titleId),
  });

  // My List status (best-effort; ignore failures)
  const watchlist = useQuery({
    queryKey: ["watchlist"],
    queryFn: () => me.listWatchlist(),
    enabled: isLoggedIn,
  });
  const reactions = useQuery({
    queryKey: ["reactions"],
    queryFn: () => me.reactions(),
    enabled: isLoggedIn,
  });

  const inList = watchlist.data?.items.some((w) => w.title.id === titleId);
  const currentReaction = reactions.data?.items.find((r) => r.title.id === titleId)?.kind;

  const addM = useMutation({
    mutationFn: () => me.addToList(titleId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["watchlist"] }),
  });
  const rmM = useMutation({
    mutationFn: () => me.removeFromList(titleId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["watchlist"] }),
  });
  const reactM = useMutation({
    mutationFn: (kind: "thumbs_down" | "thumbs_up" | "double_thumbs_up") =>
      me.setReaction(titleId, kind),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["reactions"] }),
  });
  const clearReactM = useMutation({
    mutationFn: () => me.clearReaction(titleId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["reactions"] }),
  });

  if (isLoading) return <div className="p-8 text-white/60">Loading…</div>;
  if (!title) return <div className="p-8 text-white/60">Title not found.</div>;

  return (
    <div>
      {/* Backdrop hero */}
      <div className="relative h-[40vh] md:h-[60vh] w-full overflow-hidden">
        {title.backdrop_url || title.poster_url ? (
          <img
            src={title.backdrop_url || title.poster_url || ""}
            alt={title.title}
            className="absolute inset-0 h-full w-full object-cover"
          />
        ) : (
          <div className="absolute inset-0 bg-gradient-to-br from-[var(--color-bg-surface)] to-[var(--color-bg-elevated)]" />
        )}
        <div className="absolute inset-0 bg-gradient-to-t from-black via-black/70 to-black/20" />
      </div>

      <div className="-mt-32 md:-mt-48 relative z-10 px-4 md:px-8 lg:px-[60px] pb-16 max-w-[1100px]">
        <h1 className="text-[2rem] md:text-[3rem] font-extrabold leading-tight text-white">
          {title.title}
        </h1>
        <div className="mt-3 flex flex-wrap items-center gap-3 text-sm text-white/70">
          {title.age_rating && (
            <span className="rounded border border-white/40 px-2 py-0.5">{title.age_rating}</span>
          )}
          {title.release_year && <span>{title.release_year}</span>}
          {title.runtime_minutes && <span>{title.runtime_minutes} min</span>}
          {title.type === "series" && <span>{title.seasons.length} Season{title.seasons.length === 1 ? "" : "s"}</span>}
          {title.is_free && (
            <span className="rounded bg-[var(--color-brand)] px-2 py-0.5 text-xs font-bold tracking-wider text-white">
              FREE
            </span>
          )}
        </div>

        {title.synopsis && <p className="mt-5 max-w-[640px] text-base text-white/90">{title.synopsis}</p>}

        {/* CTAs */}
        <div className="mt-6 flex flex-wrap gap-3">
          {title.type === "movie" ? (
            <Link
              to={`/watch/title/${title.id}`}
              className="inline-flex items-center gap-2 rounded bg-white px-7 py-3 font-semibold text-black hover:bg-white/85"
            >
              <Play size={18} className="fill-current" /> Play
            </Link>
          ) : (
            <Link
              to={`/title/${title.id}/season/1`}
              className="inline-flex items-center gap-2 rounded bg-white px-7 py-3 font-semibold text-black hover:bg-white/85"
            >
              <Play size={18} className="fill-current" /> Play S1E1
            </Link>
          )}
          {title.trailer_url && (
            <a
              href={title.trailer_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-2 rounded bg-white/15 px-7 py-3 font-semibold text-white hover:bg-white/25"
            >
              Watch Trailer
            </a>
          )}
          {isLoggedIn && (
            <>
              <button
                type="button"
                className="grid h-12 w-12 place-items-center rounded-full border border-white/40 text-white hover:border-white"
                onClick={() => (inList ? rmM.mutate() : addM.mutate())}
                aria-label={inList ? "Remove from My List" : "Add to My List"}
                title={inList ? "Remove from My List" : "Add to My List"}
              >
                {inList ? <Check size={20} /> : <Plus size={20} />}
              </button>
              <ReactionButtons current={currentReaction} onSet={(k) => reactM.mutate(k)} onClear={() => clearReactM.mutate()} />
            </>
          )}
        </div>

        {/* Genres */}
        {title.genres.length > 0 && (
          <div className="mt-8 flex flex-wrap gap-2 text-sm">
            {title.genres.map((g) => (
              <Link
                key={g.id}
                to={`/browse?genre=${g.slug}`}
                className="rounded border border-white/20 px-2.5 py-1 text-white/80 hover:bg-white/10"
              >
                {g.name}
              </Link>
            ))}
          </div>
        )}

        {/* Languages */}
        {(title.audio_tracks.length > 0 || title.subtitle_tracks.length > 0) && (
          <div className="mt-8 grid grid-cols-1 gap-3 md:grid-cols-2">
            {title.audio_tracks.length > 0 && (
              <div>
                <div className="text-xs uppercase tracking-wider text-white/50">Audio</div>
                <div className="text-sm text-white/80">
                  {title.audio_tracks.map((t) => `${t.language.toUpperCase()} (${t.kind})`).join(" · ")}
                </div>
              </div>
            )}
            {title.subtitle_tracks.length > 0 && (
              <div>
                <div className="text-xs uppercase tracking-wider text-white/50">Subtitles</div>
                <div className="text-sm text-white/80">
                  {title.subtitle_tracks.map((t) => `${t.language.toUpperCase()} (${t.kind})`).join(" · ")}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Series — season list */}
        {title.type === "series" && title.seasons.length > 0 && (
          <section className="mt-10">
            <h2 className="text-[1.4rem] font-semibold mb-3">Seasons</h2>
            <ul className="space-y-2">
              {title.seasons.map((s) => (
                <li key={s.id}>
                  <Link
                    to={`/title/${title.id}/season/${s.season_number}`}
                    className="flex items-center justify-between rounded border border-white/10 bg-[var(--color-bg-elevated)] px-4 py-3 hover:border-white/30"
                  >
                    <span className="font-medium">
                      {s.name || `Season ${s.season_number}`}
                    </span>
                    <span className="text-sm text-white/60">
                      {s.episode_count} episode{s.episode_count === 1 ? "" : "s"}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        )}
      </div>
    </div>
  );
}

function ReactionButtons({
  current,
  onSet,
  onClear,
}: {
  current: string | undefined;
  onSet: (k: "thumbs_down" | "thumbs_up" | "double_thumbs_up") => void;
  onClear: () => void;
}) {
  function toggle(k: "thumbs_down" | "thumbs_up" | "double_thumbs_up") {
    if (current === k) onClear();
    else onSet(k);
  }
  const btn =
    "grid h-12 w-12 place-items-center rounded-full border border-white/40 text-white transition-colors hover:border-white";
  return (
    <>
      <button
        type="button"
        className={btn + (current === "thumbs_down" ? " bg-white/20" : "")}
        onClick={() => toggle("thumbs_down")}
        aria-label="Not for me"
      >
        <ThumbsDown size={20} />
      </button>
      <button
        type="button"
        className={btn + (current === "thumbs_up" ? " bg-white/20" : "")}
        onClick={() => toggle("thumbs_up")}
        aria-label="I like this"
      >
        <ThumbsUp size={20} />
      </button>
      <button
        type="button"
        className={btn + (current === "double_thumbs_up" ? " bg-[var(--color-brand)] border-[var(--color-brand)]" : "")}
        onClick={() => toggle("double_thumbs_up")}
        aria-label="Love this"
      >
        <Heart size={20} />
      </button>
    </>
  );
}
