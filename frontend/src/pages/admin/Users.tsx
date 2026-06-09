import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { admin } from "../../api";

export default function AdminUsers() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["admin", "users"],
    queryFn: () => admin.users(1, 100),
  });
  const changeM = useMutation({
    mutationFn: ({ id, role }: { id: number; role: string }) => admin.changeUserRole(id, role),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "users"] }),
  });
  return (
    <div>
      <h1 className="mb-6 text-[2rem] font-bold">Users</h1>
      {isLoading && <div className="text-white/60">Loading…</div>}
      {data && (
        <div className="overflow-x-auto rounded border border-white/10">
          <table className="w-full text-sm">
            <thead className="bg-[var(--color-bg-elevated)] text-left text-xs uppercase tracking-wider text-white/60">
              <tr>
                <th className="px-4 py-3">Email</th>
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">Role</th>
                <th className="px-4 py-3">Active?</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {data.items.map((u) => (
                <tr key={u.id} className="hover:bg-white/5">
                  <td className="px-4 py-2.5 font-medium">{u.email}</td>
                  <td className="px-4 py-2.5 text-white/70">{u.full_name ?? "—"}</td>
                  <td className="px-4 py-2.5">
                    <select
                      value={u.role}
                      onChange={(e) => changeM.mutate({ id: u.id, role: e.target.value })}
                      className="rounded border border-white/20 bg-[var(--color-bg-surface)] px-2 py-1"
                    >
                      <option value="user">user</option>
                      <option value="viewer">viewer</option>
                      <option value="content_manager">content_manager</option>
                      <option value="admin">admin</option>
                    </select>
                  </td>
                  <td className="px-4 py-2.5">{u.is_active ? "Yes" : "—"}</td>
                  <td className="px-4 py-2.5 text-right text-white/40">{new Date(u.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
