import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { ChevronDown, ChevronRight, Plus, Upload as UploadIcon } from "lucide-react";
import { admin } from "../../api";
import { apiErrorMessage } from "../../api/client";
import type { Episode, SeasonDetail, TitleStatus } from "../../api/types";

/**
 * Admin seasons & episodes editor — /admin/titles/:id/seasons.
 *
 * Linked from TitleEditor for series titles. Uses the admin season list
 * (admin.listSeasons) which returns EVERY season + episode regardless of
 * status — the public season endpoint hides drafts, so it can't drive an
 * admin screen.
 *
 * Layout: one card per season; each season lists its episodes as expandable
 * rows (edit metadata, skip markers, publish/delete, video + subtitle upload),
 * plus an "Add episode" form at the bottom of the card.
 */
export default function SeasonsEditor() {
  const { id } = useParams();
  const titleId = Number(id);
  const qc = useQueryClient();

  const title = useQuery({
    queryKey: ["admin", "title", titleId],
    queryFn: () => admin.getTitle(titleId),
    enabled: Number.isFinite(titleId),
  });
  const seasons = useQuery({
    queryKey: ["admin", "seasons", titleId],
    queryFn: () => admin.listSeasons(titleId),
    enabled: Number.isFinite(titleId),
  });

  // Every mutation below funnels through this — one refetch path keeps the
  // whole page consistent after any write.
  const refetchSeasons = () =>
    qc.invalidateQueries({ queryKey: ["admin", "seasons", titleId] });

  return (
    <div>
      <Link to={`/admin/titles/${titleId}`} className="text-sm text-white/60 hover:text-white">
        ← Back to title
      </Link>
      <h1 className="mt-2 text-[2rem] font-bold">
        Seasons{title.data ? ` — ${title.data.title}` : ""}
      </h1>

      {seasons.isLoading && <div className="mt-6 text-white/60">Loading…</div>}
      {seasons.isError && (
        <div className="mt-6 rounded border border-red-500/50 bg-red-500/10 p-3 text-sm text-red-200">
          {apiErrorMessage(seasons.error, "Couldn't load seasons.")}
        </div>
      )}

      <div className="mt-6 space-y-5">
        {seasons.data?.map((s) => (
          <SeasonCard key={s.id} season={s} onChanged={refetchSeasons} />
        ))}
        {seasons.data?.length === 0 && (
          <div className="rounded border border-white/10 bg-[var(--color-bg-elevated)] p-5 text-sm text-white/60">
            No seasons yet — create the first one below.
          </div>
        )}
      </div>

      <CreateSeasonCard
        titleId={titleId}
        nextSeasonNumber={(seasons.data?.length ?? 0) + 1}
        onCreated={refetchSeasons}
      />
    </div>
  );
}

/** Small colored status pill — same statuses as titles (draft/published/…). */
function StatusBadge({ status }: { status: TitleStatus }) {
  const styles: Record<TitleStatus, string> = {
    draft: "bg-white/10 text-white/70",
    scheduled: "bg-amber-500/15 text-amber-300",
    published: "bg-green-500/15 text-green-300",
    archived: "bg-white/10 text-white/50",
    removed: "bg-red-500/15 text-red-300",
  };
  return (
    <span className={`rounded px-2 py-0.5 text-[11px] uppercase tracking-wider ${styles[status]}`}>
      {status}
    </span>
  );
}

function CreateSeasonCard({
  titleId,
  nextSeasonNumber,
  onCreated,
}: {
  titleId: number;
  nextSeasonNumber: number;
  onCreated: () => void;
}) {
  const [number, setNumber] = useState("");
  const [name, setName] = useState("");
  const [err, setErr] = useState<string | null>(null);

  const createM = useMutation({
    mutationFn: () =>
      admin.createSeason(titleId, {
        season_number: Number(number || nextSeasonNumber),
        name: name.trim() || undefined,
      }),
    onSuccess: () => {
      onCreated();
      setNumber("");
      setName("");
      setErr(null);
    },
    onError: (e) => setErr(apiErrorMessage(e)),
  });

  return (
    <div className="mt-6 rounded border border-white/10 bg-[var(--color-bg-elevated)] p-5">
      <h3 className="text-sm uppercase tracking-wider text-white/60">New season</h3>
      <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-[120px_1fr_auto]">
        <input
          type="number"
          min={1}
          className="input-base text-sm"
          placeholder={`Number (${nextSeasonNumber})`}
          value={number}
          onChange={(e) => setNumber(e.target.value)}
        />
        <input
          className="input-base text-sm"
          placeholder="Name (optional)"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <button
          type="button"
          className="btn-primary !py-2 !px-4 text-sm"
          disabled={createM.isPending}
          onClick={() => createM.mutate()}
        >
          <Plus size={16} /> {createM.isPending ? "Creating…" : "Create season"}
        </button>
      </div>
      {err && <div className="mt-3 text-sm text-red-300">{err}</div>}
    </div>
  );
}

function SeasonCard({ season, onChanged }: { season: SeasonDetail; onChanged: () => void }) {
  return (
    <div className="rounded border border-white/10 bg-[var(--color-bg-elevated)] p-5">
      <h2 className="text-lg font-semibold">
        Season {season.season_number}
        {season.name && <span className="ml-2 font-normal text-white/60">{season.name}</span>}
      </h2>

      <div className="mt-4 space-y-2">
        {season.episodes.map((ep) => (
          <EpisodeRow key={ep.id} episode={ep} onChanged={onChanged} />
        ))}
        {season.episodes.length === 0 && (
          <div className="text-sm text-white/50">No episodes yet.</div>
        )}
      </div>

      <CreateEpisodeForm
        seasonId={season.id}
        nextEpisodeNumber={season.episodes.length + 1}
        onCreated={onChanged}
      />
    </div>
  );
}

/**
 * One episode — collapsed row with status + quick actions; expands to show
 * the metadata/markers edit form and the video + subtitle upload cards.
 */
function EpisodeRow({ episode, onChanged }: { episode: Episode; onChanged: () => void }) {
  const [open, setOpen] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const publishM = useMutation({
    mutationFn: () => admin.publishEpisode(episode.id),
    onSuccess: () => {
      onChanged();
      setErr(null);
    },
    onError: (e) => setErr(apiErrorMessage(e)),
  });
  const deleteM = useMutation({
    mutationFn: () => admin.deleteEpisode(episode.id),
    onSuccess: onChanged,
    onError: (e) => setErr(apiErrorMessage(e)),
  });

  return (
    <div className="rounded bg-black/30">
      <div className="flex flex-wrap items-center gap-3 px-3 py-2">
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="flex min-w-0 flex-1 items-center gap-2 text-left text-sm hover:text-white"
          aria-expanded={open}
        >
          {open ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
          <span className="font-medium">E{episode.episode_number}</span>
          <span className="truncate text-white/80">{episode.name}</span>
        </button>
        <StatusBadge status={episode.status} />
        {episode.status === "draft" && (
          <button
            type="button"
            className="rounded border border-white/20 px-2.5 py-1 text-xs hover:border-white/50"
            disabled={publishM.isPending}
            onClick={() => publishM.mutate()}
          >
            {publishM.isPending ? "Publishing…" : "Publish"}
          </button>
        )}
        <button
          type="button"
          className="rounded border border-red-500/40 px-2.5 py-1 text-xs text-red-300 hover:bg-red-500/10"
          onClick={() => {
            if (confirm(`Delete episode ${episode.episode_number} — "${episode.name}"?`))
              deleteM.mutate();
          }}
        >
          Delete
        </button>
      </div>
      {err && <div className="px-3 pb-2 text-sm text-red-300">{err}</div>}

      {open && (
        <div className="grid gap-5 border-t border-white/10 p-4 md:grid-cols-2">
          <EpisodeEditForm episode={episode} onSaved={onChanged} />
          <div className="space-y-4">
            <EpisodeVideoUpload episodeId={episode.id} onDone={onChanged} />
            <EpisodeSubtitleUpload episodeId={episode.id} />
          </div>
        </div>
      )}
    </div>
  );
}

/** Shared shape for the episode form fields — everything as strings so empty
 *  inputs are easy to distinguish from 0, converted to numbers on submit. */
type EpisodeFormValues = {
  episode_number: string;
  ordinal: string;
  name: string;
  synopsis: string;
  runtime_seconds: string;
  intro_start_sec: string;
  intro_end_sec: string;
  recap_start_sec: string;
  recap_end_sec: string;
};

/** "" → null, otherwise Number. Markers + runtime are optional integers. */
function toIntOrNull(v: string): number | null {
  return v.trim() === "" ? null : Number(v);
}

/** The four skip-marker inputs, collapsed by default — most episodes are
 *  created without markers and they get filled in later. */
function MarkerFields({
  values,
  onChange,
}: {
  values: EpisodeFormValues;
  onChange: (patch: Partial<EpisodeFormValues>) => void;
}) {
  const [open, setOpen] = useState(false);
  const markers = [
    { key: "intro_start_sec", label: "Intro start (sec)" },
    { key: "intro_end_sec", label: "Intro end (sec)" },
    { key: "recap_start_sec", label: "Recap start (sec)" },
    { key: "recap_end_sec", label: "Recap end (sec)" },
  ] as const;
  return (
    <div>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1 text-xs uppercase tracking-wider text-white/60 hover:text-white"
        aria-expanded={open}
      >
        {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        Skip markers (intro / recap)
      </button>
      {open && (
        <div className="mt-2 grid grid-cols-2 gap-2">
          {markers.map((m) => (
            <div key={m.key}>
              <label className="block text-[11px] text-white/50">{m.label}</label>
              <input
                type="number"
                min={0}
                className="input-base text-sm"
                value={values[m.key]}
                onChange={(e) => onChange({ [m.key]: e.target.value })}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function CreateEpisodeForm({
  seasonId,
  nextEpisodeNumber,
  onCreated,
}: {
  seasonId: number;
  nextEpisodeNumber: number;
  onCreated: () => void;
}) {
  const emptyForm: EpisodeFormValues = {
    episode_number: "",
    ordinal: "",
    name: "",
    synopsis: "",
    runtime_seconds: "",
    intro_start_sec: "",
    intro_end_sec: "",
    recap_start_sec: "",
    recap_end_sec: "",
  };
  const [open, setOpen] = useState(false);
  const [f, setF] = useState(emptyForm);
  const [err, setErr] = useState<string | null>(null);
  const patch = (p: Partial<EpisodeFormValues>) => setF((prev) => ({ ...prev, ...p }));

  const createM = useMutation({
    mutationFn: () => {
      const episodeNumber = Number(f.episode_number || nextEpisodeNumber);
      return admin.createEpisode(seasonId, {
        episode_number: episodeNumber,
        // Ordinal = global playback order across seasons; defaults to the
        // episode number when the admin doesn't care to override it.
        ordinal: f.ordinal ? Number(f.ordinal) : episodeNumber,
        name: f.name.trim(),
        synopsis: f.synopsis.trim() || null,
        runtime_seconds: toIntOrNull(f.runtime_seconds),
        intro_start_sec: toIntOrNull(f.intro_start_sec),
        intro_end_sec: toIntOrNull(f.intro_end_sec),
        recap_start_sec: toIntOrNull(f.recap_start_sec),
        recap_end_sec: toIntOrNull(f.recap_end_sec),
      });
    },
    onSuccess: () => {
      onCreated();
      setF(emptyForm);
      setOpen(false);
      setErr(null);
    },
    onError: (e) => setErr(apiErrorMessage(e)),
  });

  if (!open) {
    return (
      <button
        type="button"
        className="mt-4 flex items-center gap-1.5 text-sm text-white/70 hover:text-white"
        onClick={() => setOpen(true)}
      >
        <Plus size={16} /> Add episode
      </button>
    );
  }

  return (
    <div className="mt-4 rounded border border-white/10 p-4">
      <h4 className="text-xs uppercase tracking-wider text-white/60">New episode</h4>
      <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
        <div>
          <label className="block text-[11px] text-white/50">Episode #</label>
          <input
            type="number"
            min={1}
            className="input-base text-sm"
            placeholder={String(nextEpisodeNumber)}
            value={f.episode_number}
            onChange={(e) => patch({ episode_number: e.target.value })}
          />
        </div>
        <div>
          <label className="block text-[11px] text-white/50">Ordinal (play order)</label>
          <input
            type="number"
            min={1}
            className="input-base text-sm"
            placeholder="same as #"
            value={f.ordinal}
            onChange={(e) => patch({ ordinal: e.target.value })}
          />
        </div>
        <div>
          <label className="block text-[11px] text-white/50">Runtime (sec)</label>
          <input
            type="number"
            min={1}
            className="input-base text-sm"
            value={f.runtime_seconds}
            onChange={(e) => patch({ runtime_seconds: e.target.value })}
          />
        </div>
      </div>
      <label className="mt-2 block text-[11px] text-white/50">Name</label>
      <input
        className="input-base text-sm"
        value={f.name}
        onChange={(e) => patch({ name: e.target.value })}
      />
      <label className="mt-2 block text-[11px] text-white/50">Synopsis (optional)</label>
      <textarea
        className="input-base min-h-[60px] text-sm"
        value={f.synopsis}
        onChange={(e) => patch({ synopsis: e.target.value })}
      />
      <div className="mt-3">
        <MarkerFields values={f} onChange={patch} />
      </div>
      {err && <div className="mt-3 text-sm text-red-300">{err}</div>}
      <div className="mt-4 flex gap-2">
        <button
          type="button"
          className="btn-primary !py-2 !px-4 text-sm"
          disabled={createM.isPending || !f.name.trim()}
          onClick={() => createM.mutate()}
        >
          {createM.isPending ? "Creating…" : "Create episode"}
        </button>
        <button
          type="button"
          className="btn-ghost !py-2 !px-4 text-sm"
          onClick={() => {
            setOpen(false);
            setErr(null);
          }}
        >
          Cancel
        </button>
      </div>
    </div>
  );
}

function EpisodeEditForm({ episode, onSaved }: { episode: Episode; onSaved: () => void }) {
  const [f, setF] = useState<EpisodeFormValues>({
    episode_number: String(episode.episode_number),
    ordinal: String(episode.ordinal),
    name: episode.name,
    synopsis: episode.synopsis ?? "",
    runtime_seconds: episode.runtime_seconds?.toString() ?? "",
    intro_start_sec: episode.intro_start_sec?.toString() ?? "",
    intro_end_sec: episode.intro_end_sec?.toString() ?? "",
    recap_start_sec: episode.recap_start_sec?.toString() ?? "",
    recap_end_sec: episode.recap_end_sec?.toString() ?? "",
  });
  const [msg, setMsg] = useState<string | null>(null);
  const patch = (p: Partial<EpisodeFormValues>) => setF((prev) => ({ ...prev, ...p }));

  const updateM = useMutation({
    // episode_number is intentionally not editable — renumbering would
    // collide with siblings; the backend update schema doesn't accept it.
    mutationFn: () =>
      admin.updateEpisode(episode.id, {
        name: f.name.trim(),
        synopsis: f.synopsis.trim() || null,
        runtime_seconds: toIntOrNull(f.runtime_seconds),
        ordinal: f.ordinal ? Number(f.ordinal) : undefined,
        intro_start_sec: toIntOrNull(f.intro_start_sec),
        intro_end_sec: toIntOrNull(f.intro_end_sec),
        recap_start_sec: toIntOrNull(f.recap_start_sec),
        recap_end_sec: toIntOrNull(f.recap_end_sec),
      }),
    onSuccess: () => {
      onSaved();
      setMsg("Saved.");
      setTimeout(() => setMsg(null), 1500);
    },
    onError: (e) => setMsg(apiErrorMessage(e)),
  });

  return (
    <div className="space-y-2">
      <label className="block text-[11px] text-white/50">Name</label>
      <input
        className="input-base text-sm"
        value={f.name}
        onChange={(e) => patch({ name: e.target.value })}
      />
      <label className="block text-[11px] text-white/50">Synopsis</label>
      <textarea
        className="input-base min-h-[60px] text-sm"
        value={f.synopsis}
        onChange={(e) => patch({ synopsis: e.target.value })}
      />
      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="block text-[11px] text-white/50">Runtime (sec)</label>
          <input
            type="number"
            min={1}
            className="input-base text-sm"
            value={f.runtime_seconds}
            onChange={(e) => patch({ runtime_seconds: e.target.value })}
          />
        </div>
        <div>
          <label className="block text-[11px] text-white/50">Ordinal (play order)</label>
          <input
            type="number"
            min={1}
            className="input-base text-sm"
            value={f.ordinal}
            onChange={(e) => patch({ ordinal: e.target.value })}
          />
        </div>
      </div>
      <MarkerFields values={f} onChange={patch} />
      {msg && (
        <div className={`text-sm ${msg === "Saved." ? "text-green-300" : "text-red-300"}`}>
          {msg}
        </div>
      )}
      <button
        type="button"
        className="btn-primary !py-2 !px-4 text-sm"
        disabled={updateM.isPending || !f.name.trim()}
        onClick={() => updateM.mutate()}
      >
        {updateM.isPending ? "Saving…" : "Save changes"}
      </button>
    </div>
  );
}

/** Same upload UX as the movie upload card in TitleEditor — progress bar
 *  driven by axios onUploadProgress. */
function EpisodeVideoUpload({ episodeId, onDone }: { episodeId: number; onDone: () => void }) {
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState<string | null>(null);
  async function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setStatus("Uploading…");
    setProgress(0);
    try {
      await admin.uploadEpisodeVideo(episodeId, file, setProgress);
      setStatus("Uploaded ✓");
      onDone();
    } catch (err) {
      setStatus(apiErrorMessage(err, "Upload failed"));
    } finally {
      e.target.value = "";
    }
  }
  return (
    <div className="rounded border border-white/10 p-4">
      <h4 className="text-xs uppercase tracking-wider text-white/60">Video file</h4>
      <label className="mt-3 flex cursor-pointer items-center gap-3 rounded border border-dashed border-white/30 p-3 hover:border-white/60">
        <UploadIcon size={18} />
        <span className="text-sm">Click to choose a file</span>
        <input
          type="file"
          accept=".mp4,.mov,.m4v,.webm,.m3u8"
          className="hidden"
          onChange={onFile}
        />
      </label>
      {progress > 0 && (
        <div className="mt-3">
          <div className="h-2 overflow-hidden rounded bg-white/10">
            <div
              className="h-full bg-[var(--color-brand)] transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
          <div className="mt-1 text-xs text-white/60">{progress}%</div>
        </div>
      )}
      {status && <div className="mt-3 text-sm">{status}</div>}
    </div>
  );
}

/** Subtitle (.vtt) upload — upserts by (episode, language) server-side, so
 *  re-uploading a language replaces the prior file. */
function EpisodeSubtitleUpload({ episodeId }: { episodeId: number }) {
  const [language, setLanguage] = useState("en");
  const [kind, setKind] = useState<"subtitle" | "cc" | "sdh" | "dubtitle">("subtitle");
  const [label, setLabel] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  async function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy(true);
    setMsg(null);
    try {
      await admin.uploadEpisodeSubtitle(episodeId, file, {
        language: language.trim(),
        kind,
        label: label.trim() || undefined,
      });
      setMsg("Uploaded ✓");
      setLabel("");
    } catch (err) {
      setMsg(apiErrorMessage(err, "Subtitle upload failed."));
    } finally {
      setBusy(false);
      e.target.value = "";
    }
  }

  return (
    <div className="rounded border border-white/10 p-4">
      <h4 className="text-xs uppercase tracking-wider text-white/60">Subtitles (.vtt)</h4>
      <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-3">
        <input
          type="text"
          value={language}
          onChange={(e) => setLanguage(e.target.value)}
          placeholder="Lang (en, ta, hi)"
          maxLength={8}
          className="input-base text-sm"
        />
        <select
          value={kind}
          onChange={(e) => setKind(e.target.value as typeof kind)}
          className="input-base text-sm"
        >
          <option value="subtitle">Subtitle (translation)</option>
          <option value="cc">CC (same-language)</option>
          <option value="sdh">SDH (deaf/hard-of-hearing)</option>
          <option value="dubtitle">Dubtitle</option>
        </select>
        <input
          type="text"
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          placeholder="Label (optional)"
          maxLength={64}
          className="input-base text-sm"
        />
      </div>
      <label className="mt-3 flex cursor-pointer items-center gap-3 rounded border border-dashed border-white/30 p-3 hover:border-white/60">
        <UploadIcon size={18} />
        <span className="text-sm">{busy ? "Uploading…" : "Choose .vtt file"}</span>
        <input type="file" accept=".vtt" className="hidden" onChange={onFile} disabled={busy} />
      </label>
      {msg && (
        <div className={`mt-3 text-sm ${msg === "Uploaded ✓" ? "" : "text-red-300"}`}>{msg}</div>
      )}
    </div>
  );
}
