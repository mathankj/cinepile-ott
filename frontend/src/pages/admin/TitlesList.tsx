import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Plus } from "lucide-react";
import { catalog } from "../../api";
import type { TitleStatus, TitleSummary } from "../../api/types";

// The public list endpoint returns TitleSummary; status only appears on
// detail responses, so it's optional here until an admin list endpoint exists.
type AdminTitleRow = TitleSummary & { status?: TitleStatus };

export default function AdminTitlesList() {
  const { data, isLoading } = useQuery({
    queryKey: ["admin", "titles"],
    queryFn: () => catalog.listTitles({ page: 1, page_size: 100, sort: "-published_at" }),
  });

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-[2rem] font-bold">Titles</h1>
        <Link to="/admin/titles/new" className="btn-primary !py-2 !px-4 text-sm">
          <Plus size={16} /> New title
        </Link>
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
                  <td className="px-4 py-3 text-white/70">{(t as AdminTitleRow).status ?? "—"}</td>
                  <td className="px-4 py-3">{t.is_free ? <span className="text-[var(--color-brand)]">FREE</span> : "—"}</td>
                  <td className="px-4 py-3 text-white/70">{t.release_year ?? "—"}</td>
                  <td className="px-4 py-3 text-right">
                    <Link
                      to={`/admin/titles/${t.id}`}
                      className="rounded border border-white/20 px-3 py-1.5 hover:border-white/50"
                    >
                      Edit
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
