import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";
import { useEffect, useRef, useState } from "react";
import { ArrowLeft } from "lucide-react";
import { useTranslation } from "react-i18next";
import { catalog, playback, progress } from "../api";
import type { SeasonDetail } from "../api/types";
import VideoPlayer from "../components/player/VideoPlayer";

/**
 * Watch page — fetches a playback ticket then plays it.
 * Routes:
 *   /watch/title/:id   → movie playback
 *   /watch/episode/:id → episode playback
 *   /watch/trailer/:id → trailer playback (:id is the TITLE id; public
 *                        endpoint, no resume, no progress reporting)
 *
 * Cosmetic anti-capture: right-click block, no-download on the <video>, user-
 * select disabled, and a "Protected content — playback paused" curtain that
 * drops when the tab loses visibility (a real screen-recording trigger fires
 * visibilitychange). NONE of this stops a determined attacker — true content
 * protection requires DRM (Widevine/PlayReady/FairPlay + license server). See
 * docs/decisions/ for the DRM ADR placeholder before production launch.
 */
export default function Watch() {
  const { t } = useTranslation();
  const { kind, id } = useParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const refId = Number(id);
  const isEpisode = kind === "episode";
  const isTrailer = kind === "trailer";

  // Playback ticket — movies and episodes only. Trailers don't need one.
  const { data: ticket, isLoading: ticketLoading, error } = useQuery({
    queryKey: ["playback", kind, refId],
    queryFn: () => (isEpisode ? playback.episode(refId) : playback.movie(refId)),
    enabled: Number.isFinite(refId) && !isTrailer,
    staleTime: 0,
  });

  // Trailer URL — public endpoint, returns { trailer_url }.
  const { data: trailer, isLoading: trailerLoading, error: trailerError } = useQuery({
    queryKey: ["trailer", refId],
    queryFn: () => catalog.trailer(refId),
    enabled: Number.isFinite(refId) && isTrailer,
  });

  // Episode context: skip-intro/skip-recap markers + the data needed to find
  // the next episode. The Season page caches ["season", titleId, seasonNumber]
  // before linking here, so this is a pure cache read — no extra request. On a
  // cold deep link (no cached season) we gracefully skip markers and
  // auto-advance; plain playback still works.
  const episodeCtx = (() => {
    if (!isEpisode || !Number.isFinite(refId)) return null;
    for (const [key, season] of qc.getQueriesData<SeasonDetail>({ queryKey: ["season"] })) {
      const ep = season?.episodes.find((e) => e.id === refId);
      if (season && ep) return { titleId: Number(key[1]), season, episode: ep };
    }
    return null;
  })();

  // Save progress (not for trailers — they never report progress).
  const positionRef = useRef<number>(0);
  function handleProgress(positionSec: number, totalSec: number) {
    positionRef.current = positionSec;
    if (isEpisode) progress.postEpisode(refId, positionSec, totalSec).catch(() => {});
    else progress.postMovie(refId, positionSec, totalSec).catch(() => {});
  }

  // Next-episode auto-advance: when an episode ends we resolve the next watch
  // URL and show a 10-second countdown overlay before navigating.
  const [nextUp, setNextUp] = useState<string | null>(null);
  // /watch/episode/5 → /watch/episode/6 re-renders this same mounted
  // component, so any countdown left over from the previous episode must go.
  // Reset during render (same pattern as VideoPlayer's src change handling).
  const watchKey = `${kind}/${refId}`;
  const [prevWatchKey, setPrevWatchKey] = useState(watchKey);
  if (prevWatchKey !== watchKey) {
    setPrevWatchKey(watchKey);
    setNextUp(null);
  }

  async function resolveNextEpisodeUrl(): Promise<string | null> {
    if (!episodeCtx) return null;
    const { titleId, season, episode } = episodeCtx;
    const idx = season.episodes.findIndex((e) => e.id === episode.id);
    const nextInSeason = season.episodes.slice(idx + 1).find((e) => e.status === "published");
    if (nextInSeason) return `/watch/episode/${nextInSeason.id}`;
    // Last episode of this season → first episode of the next season, if any.
    try {
      const title = await qc.fetchQuery({
        queryKey: ["title", titleId],
        queryFn: () => catalog.detail(titleId),
      });
      const nextSeason = title.seasons.find(
        (s) => s.season_number === season.season_number + 1,
      );
      if (!nextSeason) return null;
      const detail = await qc.fetchQuery({
        queryKey: ["season", titleId, nextSeason.season_number],
        queryFn: () => catalog.season(titleId, nextSeason.season_number),
      });
      const first = detail.episodes.find((e) => e.status === "published");
      return first ? `/watch/episode/${first.id}` : null;
    } catch {
      return null;
    }
  }

  async function handleEnded() {
    if (isTrailer) {
      // Trailer finished → back to the title page it belongs to.
      nav(`/title/${refId}`);
      return;
    }
    if (!isEpisode || !episodeCtx) return;
    const url = await resolveNextEpisodeUrl();
    if (url) setNextUp(url);
    // Last episode of the last season → back to the title page.
    else nav(`/title/${episodeCtx.titleId}`);
  }

  const isLoading = isTrailer ? trailerLoading : ticketLoading;
  if (isLoading) {
    // Full-bleed black surface — no white flash, no layout shift when the
    // player takes over the same screen area.
    return (
      <div data-testid="watch-loading" className="grid h-screen place-items-center bg-black">
        <div
          className="h-8 w-8 animate-spin rounded-full border-2 border-white/20 border-t-[var(--color-brand)]"
          aria-label={t("common.loading")}
        />
      </div>
    );
  }

  const src = isTrailer ? trailer?.trailer_url : ticket?.manifest_url;
  if (error || trailerError || !src) {
    const msg =
      (error as { response?: { status?: number; data?: { detail?: { error?: { code?: string; message?: string } } } } } | undefined)
        ?.response?.data?.detail?.error?.message ??
      (isTrailer ? t("watch.trailer_error") : t("watch.playback_error"));
    const code = (error as { response?: { status?: number } } | undefined)?.response?.status;
    return (
      <div className="grid h-screen place-items-center bg-black px-4 text-center">
        <div>
          <p className="text-xl">{msg}</p>
          {code === 402 && (
            <button
              type="button"
              className="btn-primary mt-6"
              onClick={() => nav("/subscribe")}
            >
              {t("watch.view_plans")}
            </button>
          )}
          <button
            type="button"
            className="mt-4 block w-full text-sm text-white/60 hover:text-white"
            onClick={() => (isTrailer ? nav(`/title/${refId}`) : nav(-1))}
          >
            {t("watch.go_back")}
          </button>
        </div>
      </div>
    );
  }

  return (
    <WatchSurface>
      <button
        type="button"
        onClick={() => (isTrailer ? nav(`/title/${refId}`) : nav(-1))}
        className="absolute left-4 top-4 z-50 flex items-center gap-2 rounded bg-black/60 px-3 py-2 text-sm text-white backdrop-blur-sm hover:bg-black/80"
      >
        <ArrowLeft size={18} /> {t("common.back")}
      </button>
      <VideoPlayer
        src={src}
        resumeAtSec={isTrailer ? null : ticket?.resume_at_sec}
        onProgress={isTrailer ? undefined : handleProgress}
        onEnded={handleEnded}
        drm={isTrailer ? null : ticket?.drm}
        subtitles={isTrailer ? undefined : ticket?.subtitles}
        introStartSec={episodeCtx?.episode.intro_start_sec}
        introEndSec={episodeCtx?.episode.intro_end_sec}
        recapStartSec={episodeCtx?.episode.recap_start_sec}
        recapEndSec={episodeCtx?.episode.recap_end_sec}
      />
      {nextUp && (
        <NextEpisodeOverlay
          onPlay={() => {
            setNextUp(null);
            nav(nextUp);
          }}
          onCancel={() => setNextUp(null)}
        />
      )}
    </WatchSurface>
  );
}

/**
 * "Next episode in N…" countdown overlay. Auto-fires onPlay when the count
 * reaches zero; the user can jump immediately (Play now) or stay (Cancel).
 */
function NextEpisodeOverlay({
  onPlay,
  onCancel,
}: {
  onPlay: () => void;
  onCancel: () => void;
}) {
  const { t } = useTranslation();
  const [secondsLeft, setSecondsLeft] = useState(10);

  useEffect(() => {
    if (secondsLeft <= 0) {
      onPlay();
      return;
    }
    const t = setTimeout(() => setSecondsLeft((s) => s - 1), 1000);
    return () => clearTimeout(t);
  }, [secondsLeft, onPlay]);

  return (
    <div className="absolute inset-0 z-40 grid place-items-center bg-black/80 animate-fade-in">
      <div className="text-center">
        <div className="text-xl font-semibold text-white">
          {t("watch.next_episode_in", { seconds: secondsLeft })}
        </div>
        <div className="mt-6 flex items-center justify-center gap-3">
          <button type="button" className="btn-primary" onClick={onPlay}>
            {t("watch.play_now")}
          </button>
          <button type="button" className="btn-ghost" onClick={onCancel}>
            {t("common.cancel")}
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * Wrapper around the player that applies the cosmetic capture defences.
 * Lives in this file (not the player) because the curtain belongs to the page,
 * not the embed. The player itself stays reusable for trailers / previews.
 */
function WatchSurface({ children }: { children: React.ReactNode }) {
  const { t } = useTranslation();
  const surfaceRef = useRef<HTMLDivElement>(null);
  const [curtain, setCurtain] = useState(false);

  useEffect(() => {
    function onVisibility() {
      // When the tab is hidden (alt-tab, screen recorder grabbing a region in
      // background) we drop the curtain AND genuinely pause the <video> —
      // previously only the overlay showed and the audio kept playing
      // underneath. Returning to the tab does NOT auto-resume; the user
      // dismisses the curtain with the Resume button below.
      if (document.visibilityState !== "visible") {
        surfaceRef.current?.querySelector("video")?.pause();
        setCurtain(true);
      }
    }
    function onContext(e: MouseEvent) {
      // Block right-click menu so "Save video as..." doesn't appear. Cosmetic
      // only — devtools still works.
      e.preventDefault();
    }
    document.addEventListener("visibilitychange", onVisibility);
    document.addEventListener("contextmenu", onContext);
    return () => {
      document.removeEventListener("visibilitychange", onVisibility);
      document.removeEventListener("contextmenu", onContext);
    };
  }, []);

  function resume() {
    setCurtain(false);
    surfaceRef.current?.querySelector("video")?.play().catch(() => {
      // Autoplay rejection — the user can press play on the native controls.
    });
  }

  return (
    <div
      ref={surfaceRef}
      className="relative min-h-screen bg-black select-none"
      style={{ WebkitUserSelect: "none", userSelect: "none" }}
    >
      {children}
      {curtain && (
        <div className="fixed inset-0 z-[100] grid place-items-center bg-black text-white animate-fade-in">
          <div className="text-center">
            <div className="text-lg font-semibold">{t("watch.protected_title")}</div>
            <div className="mt-2 text-sm text-white/60">
              {t("watch.protected_body")}
            </div>
            <button type="button" className="btn-primary mt-6" onClick={resume}>
              {t("watch.resume")}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
