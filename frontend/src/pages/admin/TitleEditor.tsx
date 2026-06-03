import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Upload as UploadIcon } from "lucide-react";
import { admin, catalog } from "../../api";
import { apiErrorMessage } from "../../api/client";

/**
 * Admin title editor. /admin/titles/new for create, /admin/titles/:id for edit.
 * Right side: video upload (admin endpoint, multipart) with progress bar.
 */
export default function TitleEditor() {
  const { id } = useParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const isNew = id === "new" || !id;
  const titleId = isNew ? undefined : Number(id);

  const detail = useQuery({
    queryKey: ["admin", "title", titleId],
    queryFn: () => catalog.detail(titleId!),
    enabled: !!titleId,
  });

  const [form, setForm] = useState({
    slug: "",
    type: "movie" as "movie" | "series",
    title: "",
    synopsis: "",
    release_year: "",
    runtime_minutes: "",
    age_rating: "",
    original_language: "en",
    is_free: false,
    status: "draft" as "draft" | "published",
    hls_manifest_url: "",
  });

  // Hydrate form when detail loads
  if (detail.data && !form.title && form.slug === "") {
    setForm({
      slug: detail.data.slug,
      type: detail.data.type,
      title: detail.data.title,
      synopsis: detail.data.synopsis ?? "",
      release_year: detail.data.release_year?.toString() ?? "",
      runtime_minutes: detail.data.runtime_minutes?.toString() ?? "",
      age_rating: detail.data.age_rating ?? "",
      original_language: detail.data.original_language ?? "en",
      is_free: detail.data.is_free,
      status: detail.data.status === "published" ? "published" : "draft",
      hls_manifest_url: "",
    });
  }

  const [err, setErr] = useState<string | null>(null);

  const createM = useMutation({
    mutationFn: () =>
      admin.createTitle({
        ...form,
        release_year: form.release_year ? Number(form.release_year) : null,
        runtime_minutes: form.runtime_minutes ? Number(form.runtime_minutes) : null,
        hls_manifest_url: form.hls_manifest_url || null,
      }),
    onSuccess: (t) => {
      qc.invalidateQueries({ queryKey: ["admin", "titles"] });
      nav(`/admin/titles/${t.id}`);
    },
    onError: (e) => setErr(apiErrorMessage(e)),
  });

  const updateM = useMutation({
    mutationFn: () =>
      admin.updateTitle(titleId!, {
        title: form.title,
        synopsis: form.synopsis || null,
        release_year: form.release_year ? Number(form.release_year) : null,
        runtime_minutes: form.runtime_minutes ? Number(form.runtime_minutes) : null,
        age_rating: form.age_rating || null,
        original_language: form.original_language || null,
        is_free: form.is_free,
        hls_manifest_url: form.hls_manifest_url || undefined,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "title", titleId] });
      setErr("Saved.");
      setTimeout(() => setErr(null), 1500);
    },
    onError: (e) => setErr(apiErrorMessage(e)),
  });

  const publishM = useMutation({
    mutationFn: () => admin.publishTitle(titleId!),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "title", titleId] }),
  });
  const archiveM = useMutation({
    mutationFn: () => admin.archiveTitle(titleId!),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "title", titleId] }),
  });
  const deleteM = useMutation({
    mutationFn: () => admin.deleteTitle(titleId!),
    onSuccess: () => nav("/admin/titles"),
  });

  return (
    <div>
      <Link to="/admin/titles" className="text-sm text-white/60 hover:text-white">
        ← Titles
      </Link>
      <h1 className="mt-2 text-[2rem] font-bold">
        {isNew ? "New title" : detail.data?.title || "Edit title"}
      </h1>

      <div className="mt-8 grid gap-8 md:grid-cols-2">
        {/* LEFT — metadata */}
        <div className="space-y-3">
          <label className="block text-xs uppercase tracking-wider text-white/60">Slug</label>
          <input
            disabled={!isNew}
            className="input-base"
            value={form.slug}
            onChange={(e) => setForm({ ...form, slug: e.target.value })}
          />
          <label className="block text-xs uppercase tracking-wider text-white/60">Type</label>
          <select
            disabled={!isNew}
            className="input-base"
            value={form.type}
            onChange={(e) => setForm({ ...form, type: e.target.value as "movie" | "series" })}
          >
            <option value="movie">Movie</option>
            <option value="series">Series</option>
          </select>
          <label className="block text-xs uppercase tracking-wider text-white/60">Title</label>
          <input
            className="input-base"
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
          />
          <label className="block text-xs uppercase tracking-wider text-white/60">Synopsis</label>
          <textarea
            className="input-base min-h-[100px]"
            value={form.synopsis}
            onChange={(e) => setForm({ ...form, synopsis: e.target.value })}
          />
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs uppercase tracking-wider text-white/60">Year</label>
              <input
                className="input-base"
                value={form.release_year}
                onChange={(e) => setForm({ ...form, release_year: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-xs uppercase tracking-wider text-white/60">Runtime (min)</label>
              <input
                className="input-base"
                value={form.runtime_minutes}
                onChange={(e) => setForm({ ...form, runtime_minutes: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-xs uppercase tracking-wider text-white/60">Age</label>
              <input
                className="input-base"
                placeholder="U / U/A / A"
                value={form.age_rating}
                onChange={(e) => setForm({ ...form, age_rating: e.target.value })}
              />
            </div>
          </div>
          <label className="mt-2 flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.is_free}
              onChange={(e) => setForm({ ...form, is_free: e.target.checked })}
            />
            Free for unsubscribed users
          </label>
          {err && (
            <div
              className={`rounded border p-3 text-sm ${
                err === "Saved." ? "border-green-500/50 bg-green-500/10 text-green-200" : "border-red-500/50 bg-red-500/10 text-red-200"
              }`}
            >
              {err}
            </div>
          )}
          <div className="mt-4 flex flex-wrap gap-2">
            {isNew ? (
              <button className="btn-primary" onClick={() => createM.mutate()} disabled={createM.isPending}>
                {createM.isPending ? "Creating…" : "Create"}
              </button>
            ) : (
              <>
                <button className="btn-primary" onClick={() => updateM.mutate()} disabled={updateM.isPending}>
                  {updateM.isPending ? "Saving…" : "Save changes"}
                </button>
                {detail.data?.status === "draft" && (
                  <button className="btn-secondary" onClick={() => publishM.mutate()}>
                    Publish
                  </button>
                )}
                {detail.data?.status === "published" && (
                  <button className="btn-secondary" onClick={() => archiveM.mutate()}>
                    Archive
                  </button>
                )}
                <button
                  className="rounded border border-red-500/40 px-4 py-2 text-sm text-red-300 hover:bg-red-500/10"
                  onClick={() => {
                    if (confirm("Soft-delete this title?")) deleteM.mutate();
                  }}
                >
                  Delete
                </button>
              </>
            )}
          </div>
        </div>

        {/* RIGHT — upload */}
        {!isNew && titleId && detail.data?.type === "movie" && (
          <UploadCard titleId={titleId} onDone={() => qc.invalidateQueries({ queryKey: ["admin", "title", titleId] })} />
        )}
        {!isNew && detail.data?.type === "series" && (
          <div className="rounded border border-white/10 bg-[var(--color-bg-elevated)] p-5">
            <h3 className="text-sm uppercase tracking-wider text-white/60">Seasons</h3>
            <p className="mt-1 text-sm text-white/70">
              This is a series. Manage seasons and episodes (and their video uploads) from the
              {" "}
              <Link to={`/admin/titles/${titleId}/seasons`} className="text-[var(--color-brand)] underline">
                Seasons page
              </Link>
              .
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

function UploadCard({ titleId, onDone }: { titleId: number; onDone: () => void }) {
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState<string | null>(null);
  async function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setStatus("Uploading…");
    setProgress(0);
    try {
      await admin.uploadTitleVideo(titleId, file, setProgress);
      setStatus("Uploaded ✓");
      onDone();
    } catch (e) {
      setStatus(apiErrorMessage(e, "Upload failed"));
    }
  }
  return (
    <div className="rounded border border-white/10 bg-[var(--color-bg-elevated)] p-5">
      <h3 className="text-sm uppercase tracking-wider text-white/60">Video file</h3>
      <p className="mt-1 text-sm text-white/70">
        Upload an MP4/MOV/M3U8. Max 1 GB. Goes straight to B2.
      </p>
      <label className="mt-4 flex cursor-pointer items-center gap-3 rounded border border-dashed border-white/30 p-4 hover:border-white/60">
        <UploadIcon size={20} />
        <span className="text-sm">Click to choose a file</span>
        <input type="file" accept=".mp4,.mov,.m4v,.webm,.m3u8" className="hidden" onChange={onFile} />
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
