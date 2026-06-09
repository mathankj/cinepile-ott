import { NavLink, Outlet } from "react-router-dom";
import { Film, Users as UsersIcon, ScrollText, LayoutDashboard, Tags } from "lucide-react";

const NAV = [
  { to: "/admin", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/admin/titles", label: "Titles", icon: Film },
  { to: "/admin/genres", label: "Genres", icon: Tags },
  { to: "/admin/users", label: "Users", icon: UsersIcon, adminOnly: true },
  { to: "/admin/audit", label: "Audit log", icon: ScrollText, adminOnly: true },
];

export default function AdminLayout() {
  return (
    <div className="grid min-h-[80vh] grid-cols-1 md:grid-cols-[220px_1fr]">
      <aside className="border-r border-white/10 bg-[var(--color-bg-elevated)] p-4 md:p-6">
        <div className="mb-6 text-xs uppercase tracking-wider text-white/50">Admin</div>
        <nav className="flex flex-row gap-1 md:flex-col">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.end}
              className={({ isActive }) =>
                `flex items-center gap-2 rounded px-3 py-2 text-sm ${
                  isActive ? "bg-white/10 text-white" : "text-white/70 hover:bg-white/5"
                }`
              }
            >
              <n.icon size={16} /> {n.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <section className="p-4 md:p-8">
        <Outlet />
      </section>
    </div>
  );
}
