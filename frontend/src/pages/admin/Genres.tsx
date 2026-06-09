import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { admin } from "../../api";
import { apiErrorMessage } from "../../api/client";
import type { Genre } from "../../api/types";

/**
 * Admin genre management — /admin/genres.
 *
 * List + create + inline rename + delete. Deleting a genre that's still
 * attached to titles returns a 409 from the backend; we surface that message
 * verbatim so the admin knows to detach it from titles first.
 */
export default function AdminGenres() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["admin", "genres"],
    queryFn: () => admin.listGenres(),
  });
  const refetch = () => qc.invalidateQueries({ queryKey: ["admin", "genres"] });

  // One shared error slot — create/rename/delete failures all land here.
  const [err, setErr] = useState<string | null>(null);

  const [slug, setSlug] = useState("");
  const [name, setName] = useState("");
  const [kind, setKind] = useState<"primary" | "sub" | "mood">("primary");

  const createM = useMutation({
    mutationFn: () => admin.createGenre({ slug: slug.trim(), name: name.trim(), kind }),
    onSuccess: () => {
      refetch();
      setSlug("");
      setName("");
      setErr(null);
    },
    onError: (e) => setErr(apiErrorMessage(e)),
  });

  const deleteM = useMutation({
    mutationFn: (id: number) => admin.deleteGenre(id),
    onSuccess: () => {
      refetch();
      setErr(null);
    },
    // 409 "genre in use" lands here — the envelope message says which.
    onError: (e) => setErr(apiErrorMessage(e)),
  });

  return (
    <div>
      <h1 className="mb-6 text-[2rem] font-bold">Genres</h1>

      {/* Create */}
      <div className="mb-6 rounded border border-white/10 bg-[var(--color-bg-elevated)] p-5">
        <h3 className="text-sm uppercase tracking-wider text-white/60">New genre</h3>
        <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-[1fr_1fr_160px_auto]">
          <input
            className="input-base text-sm"
            placeholder="Slug (action-thriller)"
            value={slug}
            onChange={(e) => setSlug(e.target.value)}
          />
          <input
            className="input-base text-sm"
            placeholder="Name (Action Thriller)"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <select
            className="input-base text-sm"
            value={kind}
            onChange={(e) => setKind(e.target.value as typeof kind)}
          >
            <option value="primary">primary</option>
            <option value="sub">sub</option>
            <option value="mood">mood</option>
          </select>
          <button
            type="button"
            className="btn-primary !py-2 !px-4 text-sm"
            disabled={createM.isPending || !slug.trim() || !name.trim()}
            onClick={() => createM.mutate()}
          >
            <Plus size={16} /> {createM.isPending ? "Creating…" : "Create"}
          </button>
        </div>
      </div>

      {err && (
        <div className="mb-4 rounded border border-red-500/50 bg-red-500/10 p-3 text-sm text-red-200">
          {err}
        </div>
      )}

      {isLoading && <div className="text-white/60">Loading…</div>}
      {data && (
        <div className="overflow-x-auto rounded border border-white/10">
          <table className="w-full text-sm">
            <thead className="bg-[var(--color-bg-elevated)] text-left text-xs uppercase tracking-wider text-white/60">
              <tr>
                <th className="px-4 py-3">Slug</th>
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">Kind</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {data.map((g) => (
                <GenreRow
                  key={g.id}
                  genre={g}
                  onRenamed={refetch}
                  onRenameError={setErr}
                  onDelete={(id) => {
                    if (confirm(`Delete genre "${g.name}"?`)) deleteM.mutate(id);
                  }}
                />
              ))}
              {data.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-4 py-6 text-center text-white/50">
                    No genres yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

/** Row with inline rename — the name cell is an input; a Save button appears
 *  only once the value differs from the server's. */
function GenreRow({
  genre,
  onRenamed,
  onRenameError,
  onDelete,
}: {
  genre: Genre;
  onRenamed: () => void;
  onRenameError: (msg: string) => void;
  onDelete: (id: number) => void;
}) {
  const [name, setName] = useState(genre.name);
  const dirty = name.trim() !== genre.name && name.trim() !== "";

  const renameM = useMutation({
    mutationFn: () => admin.updateGenre(genre.id, { name: name.trim() }),
    onSuccess: onRenamed,
    onError: (e) => onRenameError(apiErrorMessage(e)),
  });

  return (
    <tr className="hover:bg-white/5">
      <td className="px-4 py-2.5 font-mono text-white/70">{genre.slug}</td>
      <td className="px-4 py-2.5">
        <div className="flex items-center gap-2">
          <input
            className="input-base !py-1 text-sm"
            value={name}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && dirty) renameM.mutate();
            }}
            aria-label={`Rename ${genre.slug}`}
          />
          {dirty && (
            <button
              type="button"
              className="rounded border border-white/20 px-2.5 py-1 text-xs hover:border-white/50"
              disabled={renameM.isPending}
              onClick={() => renameM.mutate()}
            >
              {renameM.isPending ? "Saving…" : "Save"}
            </button>
          )}
        </div>
      </td>
      <td className="px-4 py-2.5 text-white/70">{genre.kind}</td>
      <td className="px-4 py-2.5 text-right">
        <button
          type="button"
          className="rounded border border-red-500/40 px-2.5 py-1 text-xs text-red-300 hover:bg-red-500/10"
          onClick={() => onDelete(genre.id)}
        >
          Delete
        </button>
      </td>
    </tr>
  );
}
