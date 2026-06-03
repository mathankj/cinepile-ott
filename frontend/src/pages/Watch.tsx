import { useQuery } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";
import { useRef } from "react";
import { ArrowLeft } from "lucide-react";
import { playback, progress } from "../api";
import VideoPlayer from "../components/player/VideoPlayer";

/**
 * Watch page — fetches a playback ticket then plays it.
 * Routes:
 *   /watch/title/:id   → movie playback
 *   /watch/episode/:id → episode playback
 */
export default function Watch() {
  const { kind, id } = useParams();
  const nav = useNavigate();
  const refId = Number(id);
  const isEpisode = kind === "episode";

  const { data: ticket, isLoading, error } = useQuery({
    queryKey: ["playback", kind, refId],
    queryFn: () => (isEpisode ? playback.episode(refId) : playback.movie(refId)),
    enabled: Number.isFinite(refId),
    staleTime: 0,
  });

  // Skip-intro markers come from the season detail when present — left out of
  // this minimal player for now; Watch screen reads ticket.resume_at_sec only.

  // Save progress
  const positionRef = useRef<number>(0);
  function handleProgress(positionSec: number, totalSec: number) {
    positionRef.current = positionSec;
    if (isEpisode) progress.postEpisode(refId, positionSec, totalSec).catch(() => {});
    else progress.postMovie(refId, positionSec, totalSec).catch(() => {});
  }

  if (isLoading) {
    return <div className="grid h-screen place-items-center text-white/60">Loading playback…</div>;
  }
  if (error || !ticket) {
    const msg =
      (error as { response?: { status?: number; data?: { detail?: { error?: { code?: string; message?: string } } } } } | undefined)
        ?.response?.data?.detail?.error?.message ?? "Couldn't start playback.";
    const code = (error as { response?: { status?: number } } | undefined)?.response?.status;
    return (
      <div className="grid h-screen place-items-center px-4 text-center">
        <div>
          <p className="text-xl">{msg}</p>
          {code === 402 && (
            <button
              type="button"
              className="btn-primary mt-6"
              onClick={() => nav("/subscribe")}
            >
              View Plans
            </button>
          )}
          <button
            type="button"
            className="mt-4 block w-full text-sm text-white/60 hover:text-white"
            onClick={() => nav(-1)}
          >
            Go back
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-black min-h-screen">
      <button
        type="button"
        onClick={() => nav(-1)}
        className="absolute left-4 top-4 z-50 flex items-center gap-2 rounded bg-black/60 px-3 py-2 text-sm text-white backdrop-blur-sm hover:bg-black/80"
      >
        <ArrowLeft size={18} /> Back
      </button>
      <VideoPlayer
        src={ticket.manifest_url}
        resumeAtSec={ticket.resume_at_sec}
        onProgress={handleProgress}
      />
    </div>
  );
}
