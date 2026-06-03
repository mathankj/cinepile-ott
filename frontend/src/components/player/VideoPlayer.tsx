import { useEffect, useRef, useState } from "react";
import Hls from "hls.js";

/**
 * HLS video player.
 *
 * Props:
 * - src: manifest URL (.m3u8) or MP4
 * - resumeAtSec: where to seek on play start
 * - onProgress: (positionSec, totalSec) — fires every ~10s while playing
 * - introStart/intoEnd: optional skip-intro markers
 */
type Props = {
  src: string;
  resumeAtSec?: number | null;
  introStartSec?: number | null;
  introEndSec?: number | null;
  onProgress?: (positionSec: number, totalSec: number) => void;
  onEnded?: () => void;
  autoPlay?: boolean;
};

export default function VideoPlayer({
  src,
  resumeAtSec,
  introStartSec,
  introEndSec,
  onProgress,
  onEnded,
  autoPlay = true,
}: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [showSkipIntro, setShowSkipIntro] = useState(false);

  useEffect(() => {
    const video = videoRef.current;
    if (!video || !src) return;

    let hls: Hls | null = null;
    const isHls = src.includes(".m3u8");
    if (isHls && Hls.isSupported()) {
      hls = new Hls({
        // Reasonable defaults for OTT — tune later
        maxBufferLength: 30,
        maxMaxBufferLength: 60,
      });
      hls.loadSource(src);
      hls.attachMedia(video);
    } else {
      // Native HLS (Safari) or direct MP4
      video.src = src;
    }

    return () => {
      hls?.destroy();
    };
  }, [src]);

  // Resume on metadata load
  useEffect(() => {
    const video = videoRef.current;
    if (!video || !resumeAtSec) return;
    function onLoadedMeta() {
      if (resumeAtSec && resumeAtSec > 1) {
        video!.currentTime = resumeAtSec;
      }
    }
    video.addEventListener("loadedmetadata", onLoadedMeta);
    return () => video.removeEventListener("loadedmetadata", onLoadedMeta);
  }, [resumeAtSec]);

  // Progress reporting (every 10s)
  useEffect(() => {
    const video = videoRef.current;
    if (!video || !onProgress) return;
    let lastSent = 0;
    function onTime() {
      const now = Math.floor(video!.currentTime);
      if (now - lastSent >= 10 && video!.duration) {
        onProgress!(now, Math.floor(video!.duration));
        lastSent = now;
      }
    }
    function onPause() {
      if (video!.duration) onProgress!(Math.floor(video!.currentTime), Math.floor(video!.duration));
    }
    video.addEventListener("timeupdate", onTime);
    video.addEventListener("pause", onPause);
    return () => {
      video.removeEventListener("timeupdate", onTime);
      video.removeEventListener("pause", onPause);
    };
  }, [onProgress]);

  // Skip-intro button visibility
  useEffect(() => {
    const video = videoRef.current;
    if (!video || !introStartSec || !introEndSec) return;
    function onTime() {
      const t = video!.currentTime;
      setShowSkipIntro(t >= introStartSec! && t < introEndSec!);
    }
    video.addEventListener("timeupdate", onTime);
    return () => video.removeEventListener("timeupdate", onTime);
  }, [introStartSec, introEndSec]);

  function skipIntro() {
    if (videoRef.current && introEndSec) {
      videoRef.current.currentTime = introEndSec;
      setShowSkipIntro(false);
    }
  }

  return (
    <div className="relative w-full bg-black">
      <video
        ref={videoRef}
        controls
        autoPlay={autoPlay}
        playsInline
        onEnded={onEnded}
        className="aspect-video w-full"
      />
      {showSkipIntro && (
        <button
          type="button"
          onClick={skipIntro}
          className="absolute bottom-20 right-6 rounded border border-white/40 bg-black/80 px-4 py-2 text-sm font-semibold text-white backdrop-blur-sm transition-colors hover:bg-white hover:text-black"
        >
          Skip Intro
        </button>
      )}
    </div>
  );
}
