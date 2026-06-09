import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { admin } from "../../api";

export default function AuditLog() {
  const [page] = useState(1);
  const { data, isLoading } = useQuery({
    queryKey: ["admin", "audit", page],
    queryFn: () => admin.audit({ page, page_size: 30 }),
  });
  return (
    <div>
      <h1 className="mb-6 text-[2rem] font-bold">Audit log</h1>
      {isLoading && <div className="text-white/60">Loading…</div>}
      {data && (
        <div className="overflow-x-auto rounded border border-white/10">
          <table className="w-full text-sm">
            <thead className="bg-[var(--color-bg-elevated)] text-left text-xs uppercase tracking-wider text-white/60">
              <tr>
                <th className="px-4 py-3">When</th>
                <th className="px-4 py-3">Actor</th>
                <th className="px-4 py-3">Action</th>
                <th className="px-4 py-3">Entity</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {data.items.map((e) => (
                <tr key={e.id} className="hover:bg-white/5">
                  <td className="px-4 py-2 font-mono text-white/70">
                    {new Date(e.created_at).toLocaleString()}
                  </td>
                  <td className="px-4 py-2">
                    #{e.actor_user_id} <span className="text-white/50">({e.actor_role})</span>
                  </td>
                  <td className="px-4 py-2 font-mono text-[var(--color-brand)]">{e.action}</td>
                  <td className="px-4 py-2">{e.entity_type}#{e.entity_id}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
