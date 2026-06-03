import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Trash2 } from "lucide-react";
import { Link } from "react-router-dom";
import { progress } from "../api";

/**
 * Full viewing history — finished + in-progress + hidden-from-continue.
 * Each row has a "Remove" button that hard-deletes via the backend.
 */
export default function History() {
  const [page, setPage] = useState(1);
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["history", page],
    queryFn: () => progress.history(page, 20),
  });

  const removeM = useMutation({
    mutationFn: (titleId: number) => progress.deleteHistory(titleId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["history"] }),
  });

  return (
    <div className="px-4 md:px-8 lg:px-[60px] py-12">
      <h1 className="mb-2 text-[2rem] font-bold">Viewing Activity</h1>
      <p className="mb-8 text-sm text-white/60">
        Everything you've ever watched, finished, or paused. Removing a title here erases all your progress for it.
      </p>

      {isLoading && <div className="text-white/60">Loading…</div>}
      {data && data.items.length === 0 && (
        <div className="rounded border border-white/10 bg-[var(--color-bg-elevated)] p-8 text-center text-white/60">
          No viewing activity yet.
        </div>
      )}

      {data && data.items.length > 0 && (
        <ul className="divide-y divide-white/10">
          {data.items.map((h) => (
            <li key={h.title.id} className="flex items-center gap-4 py-4">
              <Link to={`/title/${h.title.id}`} className="flex-none">
                <div className="aspect-video w-32 overflow-hidden rounded bg-black">
                  {h.title.backdrop_url || h.title.poster_url ? (
                    <img
                      src={h.title.backdrop_url || h.title.poster_url || ""}
                      alt={h.title.title}
                      className="h-full w-full object-cover"
                    />
                  ) : null}
                </div>
              </Link>
              <div className="min-w-0 flex-1">
                <Link to={`/title/${h.title.id}`} className="font-semibold hover:underline">
                  {h.title.title}
                </Link>
                <div className="mt-0.5 text-xs text-white/60">
                  {new Date(h.last_played_at).toLocaleDateString()}
                  {h.completed
                    ? " · Finished"
                    : h.hidden_from_continue
                    ? " · Hidden from Continue Watching"
                    : ` · ${Math.floor((h.position_sec / h.total_sec) * 100)}% watched`}
                </div>
              </div>
              <button
                type="button"
                onClick={() => removeM.mutate(h.title.id)}
                className="rounded border border-white/20 px-3 py-1.5 text-sm text-white/70 hover:border-red-500 hover:text-red-400"
                aria-label="Remove"
              >
                <Trash2 size={16} />
              </button>
            </li>
          ))}
        </ul>
      )}

      {data && data.total > 20 && (
        <div className="mt-8 flex items-center justify-center gap-3">
          <button
            disabled={page <= 1}
            onClick={() => setPage(page - 1)}
            className="rounded border border-white/20 px-3 py-1.5 disabled:opacity-40"
          >
            Prev
          </button>
          <span className="text-white/60">Page {page}</span>
          <button
            disabled={page * 20 >= data.total}
            onClick={() => setPage(page + 1)}
            className="rounded border border-white/20 px-3 py-1.5 disabled:opacity-40"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
