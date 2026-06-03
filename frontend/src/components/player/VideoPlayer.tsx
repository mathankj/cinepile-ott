import { useEffect, useRef, useState } from "react";
import Hls, { type Level, type MediaPlaylist } from "hls.js";
import { Settings, Check } from "lucide-react";

/**
 * HLS video player.
 *
 * Props:
 * - src: manifest URL (.m3u8) or MP4
 * - resumeAtSec: where to seek on play start
 * - onProgress: (positionSec, totalSec) — fires every ~10s while playing
 * - introStart/intoEnd: optional skip-intro markers
 *
 * Netflix-style settings gear: opens a panel over the player that exposes
 * hls.js's level (quality), audioTracks, and subtitleTracks selectors. The
 * native <video> controls stay — the settings gear is a thin overlay above
 * the player's top-right corner.
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

type QualityOption = { label: string; index: number }; // -1 = Auto

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
  const hlsRef = useRef<Hls | null>(null);

  const [showSkipIntro, setShowSkipIntro] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);

  // Player capabilities — populated once hls.js parses the manifest.
  const [qualities, setQualities] = useState<QualityOption[]>([]);
  const [currentQuality, setCurrentQuality] = useState<number>(-1); // -1 = Auto
  const [audioTracks, setAudioTracks] = useState<MediaPlaylist[]>([]);
  const [currentAudio, setCurrentAudio] = useState<number>(-1);
  const [subtitleTracks, setSubtitleTracks] = useState<MediaPlaylist[]>([]);
  const [currentSubtitle, setCurrentSubtitle] = useState<number>(-1); // -1 = off

  useEffect(() => {
    const video = videoRef.current;
    if (!video || !src) return;

    let hls: Hls | null = null;
    const isHls = src.includes(".m3u8");

    if (isHls && Hls.isSupported()) {
      hls = new Hls({
        maxBufferLength: 30,
        maxMaxBufferLength: 60,
      });
      hlsRef.current = hls;

      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        // Build the quality menu from the levels in the manifest. Manifests
        // without per-resolution renditions yield an empty levels array — in
        // that case we just hide the quality submenu.
        const levels: Level[] = hls!.levels;
        const opts: QualityOption[] = [
          { label: "Auto", index: -1 },
          ...levels
            .map((lv, i) => ({
              label: lv.height ? `${lv.height}p` : `${Math.round(lv.bitrate / 1000)} kbps`,
              index: i,
            }))
            // Highest first
            .reverse(),
        ];
        setQualities(opts);
        setCurrentQuality(hls!.currentLevel);

        setAudioTracks([...hls!.audioTracks]);
        setCurrentAudio(hls!.audioTrack);
        setSubtitleTracks([...hls!.subtitleTracks]);
        setCurrentSubtitle(hls!.subtitleTrack);
      });

      hls.on(Hls.Events.LEVEL_SWITCHED, (_e, data) => setCurrentQuality(data.level));
      hls.on(Hls.Events.AUDIO_TRACK_SWITCHED, (_e, data) => setCurrentAudio(data.id));
      hls.on(Hls.Events.SUBTITLE_TRACK_SWITCH, (_e, data) => setCurrentSubtitle(data.id));

      hls.loadSource(src);
      hls.attachMedia(video);
    } else {
      // Native HLS (Safari) or direct MP4 — no per-track UI, but native
      // captions menu still works.
      video.src = src;
      setQualities([]);
      setAudioTracks([]);
      setSubtitleTracks([]);
    }

    return () => {
      hls?.destroy();
      hlsRef.current = null;
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

  function pickQuality(idx: number) {
    if (!hlsRef.current) return;
    hlsRef.current.currentLevel = idx;
    setCurrentQuality(idx);
  }
  function pickAudio(idx: number) {
    if (!hlsRef.current) return;
    hlsRef.current.audioTrack = idx;
    setCurrentAudio(idx);
  }
  function pickSubtitle(idx: number) {
    if (!hlsRef.current) return;
    hlsRef.current.subtitleTrack = idx;
    setCurrentSubtitle(idx);
  }

  const hasSettings = qualities.length > 0 || audioTracks.length > 1 || subtitleTracks.length > 0;

  return (
    <div className="relative w-full bg-black">
      <video
        ref={videoRef}
        controls
        autoPlay={autoPlay}
        playsInline
        onEnded={onEnded}
        controlsList="nodownload noplaybackrate noremoteplayback"
        disablePictureInPicture
        disableRemotePlayback
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

      {hasSettings && (
        <>
          <button
            type="button"
            onClick={() => setSettingsOpen((v) => !v)}
            aria-label="Playback settings"
            aria-expanded={settingsOpen}
            className="absolute right-4 top-4 grid h-10 w-10 place-items-center rounded-full bg-black/60 text-white backdrop-blur-sm transition hover:bg-black/85"
          >
            <Settings size={18} />
          </button>
          {settingsOpen && (
            <SettingsPanel
              qualities={qualities}
              currentQuality={currentQuality}
              audioTracks={audioTracks}
              currentAudio={currentAudio}
              subtitleTracks={subtitleTracks}
              currentSubtitle={currentSubtitle}
              onPickQuality={pickQuality}
              onPickAudio={pickAudio}
              onPickSubtitle={pickSubtitle}
              onClose={() => setSettingsOpen(false)}
            />
          )}
        </>
      )}
    </div>
  );
}

function SettingsPanel({
  qualities,
  currentQuality,
  audioTracks,
  currentAudio,
  subtitleTracks,
  currentSubtitle,
  onPickQuality,
  onPickAudio,
  onPickSubtitle,
  onClose,
}: {
  qualities: QualityOption[];
  currentQuality: number;
  audioTracks: MediaPlaylist[];
  currentAudio: number;
  subtitleTracks: MediaPlaylist[];
  currentSubtitle: number;
  onPickQuality: (i: number) => void;
  onPickAudio: (i: number) => void;
  onPickSubtitle: (i: number) => void;
  onClose: () => void;
}) {
  return (
    <div
      className="absolute right-4 top-16 z-30 w-[260px] rounded bg-black/95 text-sm text-white shadow-2xl ring-1 ring-white/10 animate-scale-in"
      role="dialog"
      aria-label="Playback settings"
    >
      {qualities.length > 0 && (
        <Section title="Quality">
          {qualities.map((q) => (
            <Row
              key={q.index}
              label={q.label}
              selected={q.index === currentQuality}
              onClick={() => {
                onPickQuality(q.index);
                onClose();
              }}
            />
          ))}
        </Section>
      )}
      {audioTracks.length > 1 && (
        <Section title="Audio">
          {audioTracks.map((t, i) => (
            <Row
              key={t.id ?? i}
              label={trackLabel(t)}
              selected={i === currentAudio}
              onClick={() => {
                onPickAudio(i);
                onClose();
              }}
            />
          ))}
        </Section>
      )}
      {subtitleTracks.length > 0 && (
        <Section title="Subtitles">
          <Row
            label="Off"
            selected={currentSubtitle === -1}
            onClick={() => {
              onPickSubtitle(-1);
              onClose();
            }}
          />
          {subtitleTracks.map((t, i) => (
            <Row
              key={t.id ?? i}
              label={trackLabel(t)}
              selected={i === currentSubtitle}
              onClick={() => {
                onPickSubtitle(i);
                onClose();
              }}
            />
          ))}
        </Section>
      )}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="border-b border-white/10 py-2 last:border-b-0">
      <div className="px-4 py-1 text-[11px] uppercase tracking-wider text-white/60">{title}</div>
      {children}
    </div>
  );
}

function Row({
  label,
  selected,
  onClick,
}: {
  label: string;
  selected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex w-full items-center justify-between px-4 py-2 text-left transition-colors hover:bg-white/10 ${
        selected ? "text-white" : "text-white/80"
      }`}
    >
      <span>{label}</span>
      {selected && <Check size={14} />}
    </button>
  );
}

function trackLabel(t: MediaPlaylist): string {
  // Prefer human-readable name, then BCP-47 code, then a generic fallback.
  return t.name || (t.lang ? t.lang.toUpperCase() : `Track ${t.id ?? ""}`).trim();
}
