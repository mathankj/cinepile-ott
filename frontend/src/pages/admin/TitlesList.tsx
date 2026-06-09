import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Plus } from "lucide-react";
import { catalog, admin } from "../../api";
import type { TitleStatus, TitleSummary } from "../../api/types";

// The public list endpoint returns TitleSummary; status only appears on
// detail responses, so it's optional here until an admin list endpoint exists.
type AdminTitleRow = TitleSummary & { status?: TitleStatus };

export default function AdminTitlesList() {
  const qc = useQueryClient();
  // "active" = the regular catalog list; "deleted" = soft-deleted titles
  // (admin-only endpoint) with a Restore action per row.
  const [view, setView] = useState<"active" | "deleted">("active");

  const activeQ = useQuery({
    queryKey: ["admin", "titles"],
    queryFn: () => catalog.listTitles({ page: 1, page_size: 100, sort: "-published_at" }),
  });
  const deletedQ = useQuery({
    queryKey: ["admin", "titles", "deleted"],
    queryFn: () => admin.deletedTitles(),
    enabled: view === "deleted",
  });

  const restoreM = useMutation({
    mutationFn: (id: number) => admin.restoreTitle(id),
    // Prefix match on ["admin", "titles"] refetches BOTH the active list and
    // the deleted list, so the restored title moves between tabs immediately.
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "titles"] }),
  });

  const { data, isLoading } = view === "active" ? activeQ : deletedQ;

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-[2rem] font-bold">Titles</h1>
        <Link to="/admin/titles/new" className="btn-primary !py-2 !px-4 text-sm">
          <Plus size={16} /> New title
        </Link>
      </div>

      {/* Active | Deleted toggle */}
      <div className="mb-4 flex gap-1 rounded border border-white/10 bg-[var(--color-bg-elevated)] p-1 w-fit">
        {(["active", "deleted"] as const).map((v) => (
          <button
            key={v}
            type="button"
            onClick={() => setView(v)}
            className={`rounded px-4 py-1.5 text-sm capitalize transition-colors duration-200 ${
              view === v ? "bg-white/10 text-white" : "text-white/60 hover:text-white"
            }`}
          >
            {v}
          </button>
        ))}
      </div>

      {isLoading && <div className="text-white/60">Loading…</div>}
      {data && (
        <div className="overflow-x-auto rounded border border-white/10">
          <table className="w-full text-sm">
            <thead className="bg-[var(--color-bg-elevated)] text-left text-xs uppercase tracking-wider text-white/60">
              <tr>
                <th className="px-4 py-3">Title</th>
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Free?</th>
                <th className="px-4 py-3">Year</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {data.items.map((t) => (
                <tr key={t.id} className="hover:bg-white/5">
                  <td className="px-4 py-3 font-medium">{t.title}</td>
                  <td className="px-4 py-3 text-white/70">{t.type}</td>
                  <td className="px-4 py-3 text-white/70">
                    {view === "deleted" ? "deleted" : (t as AdminTitleRow).status ?? "—"}
                  </td>
                  <td className="px-4 py-3">{t.is_free ? <span className="text-[var(--color-brand)]">FREE</span> : "—"}</td>
                  <td className="px-4 py-3 text-white/70">{t.release_year ?? "—"}</td>
                  <td className="px-4 py-3 text-right">
                    {view === "active" ? (
                      <Link
                        to={`/admin/titles/${t.id}`}
                        className="rounded border border-white/20 px-3 py-1.5 hover:border-white/50"
                      >
                        Edit
                      </Link>
                    ) : (
                      <button
                        type="button"
                        className="rounded border border-white/20 px-3 py-1.5 hover:border-white/50"
                        disabled={restoreM.isPending}
                        onClick={() => restoreM.mutate(t.id)}
                      >
                        Restore
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              {data.items.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-6 text-center text-white/50">
                    {view === "deleted" ? "No deleted titles." : "No titles yet."}
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
