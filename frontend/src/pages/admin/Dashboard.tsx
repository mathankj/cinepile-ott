import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { admin, catalog } from "../../api";

export default function AdminDashboard() {
  const titlesQ = useQuery({
    queryKey: ["admin", "titles-count"],
    queryFn: () => catalog.listTitles({ page: 1, page_size: 1 }),
  });
  const auditQ = useQuery({
    queryKey: ["admin", "audit-recent"],
    queryFn: () => admin.audit({ page: 1, page_size: 10 }),
  });

  return (
    <div>
      <h1 className="mb-8 text-[2rem] font-bold">Dashboard</h1>
      <div className="grid gap-4 md:grid-cols-3">
        <Stat
          label="Published titles"
          value={titlesQ.data?.total ?? "—"}
          to="/admin/titles"
        />
        <Stat label="Recent audit entries" value={(auditQ.data as any)?.total ?? "—"} to="/admin/audit" />
        <Stat
          label="Quick action"
          value="+ New title"
          to="/admin/titles/new"
        />
      </div>

      <h2 className="mt-12 mb-4 text-[1.4rem] font-semibold">Recent activity</h2>
      <ul className="divide-y divide-white/10 rounded border border-white/10 bg-[var(--color-bg-elevated)]">
        {((auditQ.data as any)?.items ?? []).slice(0, 8).map((e: any) => (
          <li key={e.id} className="flex items-center justify-between px-4 py-2.5 text-sm">
            <div className="flex gap-3">
              <span className="font-mono text-white/50">{new Date(e.created_at).toLocaleString()}</span>
              <span className="font-mono text-[var(--color-brand)]">{e.action}</span>
              <span className="text-white/70">{e.entity_type}#{e.entity_id}</span>
            </div>
            <div className="text-white/50">by user #{e.actor_user_id}</div>
          </li>
        ))}
      </ul>
    </div>
  );
}

function Stat({ label, value, to }: { label: string; value: string | number; to: string }) {
  return (
    <Link
      to={to}
      className="block rounded border border-white/10 bg-[var(--color-bg-elevated)] p-5 hover:border-white/30"
    >
      <div className="text-xs uppercase tracking-wider text-white/50">{label}</div>
      <div className="mt-2 text-2xl font-bold">{value}</div>
    </Link>
  );
}
