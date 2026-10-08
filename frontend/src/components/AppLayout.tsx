import clsx from "clsx";
import { Headset, LayoutDashboard, ListChecks, LogOut, Menu, Plus, X } from "lucide-react";
import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useAuth, useCurrentUser } from "../auth/AuthContext";
import { ROLE_LABEL } from "../lib/labels";
import { Avatar } from "./ui";

const NAVIGATION = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/tickets", label: "Chamados", icon: ListChecks, end: true },
  { to: "/tickets/new", label: "Abrir chamado", icon: Plus, end: true },
];

function Brand() {
  return (
    <div className="flex items-center gap-2.5">
      <span className="flex size-8 items-center justify-center rounded-lg bg-indigo-600 text-white">
        <Headset className="size-4" aria-hidden />
      </span>
      <span className="text-base font-semibold tracking-tight text-white">HelpDesk Pro</span>
    </div>
  );
}

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const user = useCurrentUser();
  const { logout } = useAuth();
  const fullName = `${user.first_name} ${user.last_name}`;

  return (
    <div className="flex h-full flex-col bg-slate-900 px-4 py-5">
      <Brand />
      <nav className="mt-8 flex-1" aria-label="Navegação principal">
        <ul className="space-y-1">
          {NAVIGATION.map(({ to, label, icon: Icon, end }) => (
            <li key={to}>
              <NavLink
                to={to}
                end={end}
                onClick={onNavigate}
                className={({ isActive }) =>
                  clsx(
                    "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-slate-800 text-white"
                      : "text-slate-400 hover:bg-slate-800/60 hover:text-white",
                  )
                }
              >
                <Icon className="size-4 shrink-0" aria-hidden />
                {label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
      <div className="border-t border-slate-800 pt-4">
        <div className="flex items-center gap-3 px-1">
          <Avatar name={fullName} size="md" />
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-white">{fullName}</p>
            <p className="truncate text-xs text-slate-400">{ROLE_LABEL[user.role]}</p>
          </div>
          <button
            type="button"
            onClick={() => void logout()}
            className="rounded-md p-2 text-slate-400 hover:bg-slate-800 hover:text-white"
            aria-label="Sair"
            title="Sair"
          >
            <LogOut className="size-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

export function AppLayout() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();

  // Fecha a gaveta ao trocar de página e permite fechar com Esc.
  useEffect(() => setMobileOpen(false), [location.pathname]);
  useEffect(() => {
    if (!mobileOpen) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setMobileOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [mobileOpen]);

  return (
    <div className="min-h-screen">
      {/* Desktop: barra lateral fixa */}
      <aside className="fixed inset-y-0 left-0 hidden w-64 lg:block">
        <SidebarContent />
      </aside>

      {/* Mobile: barra superior + gaveta */}
      <header className="sticky top-0 z-30 flex h-14 items-center gap-3 bg-slate-900 px-4 lg:hidden">
        <button
          type="button"
          onClick={() => setMobileOpen(true)}
          className="-ml-2 rounded-md p-2 text-slate-300 hover:bg-slate-800 hover:text-white"
          aria-label="Abrir menu"
          aria-expanded={mobileOpen}
        >
          <Menu className="size-5" />
        </button>
        <Brand />
      </header>
      {mobileOpen && (
        <div className="fixed inset-0 z-40 lg:hidden" role="dialog" aria-modal="true" aria-label="Menu">
          <div className="absolute inset-0 bg-slate-900/60" onClick={() => setMobileOpen(false)} />
          <div className="absolute inset-y-0 left-0 w-72 max-w-[85%] shadow-xl">
            <SidebarContent onNavigate={() => setMobileOpen(false)} />
            <button
              type="button"
              onClick={() => setMobileOpen(false)}
              className="absolute right-3 top-4 rounded-md p-2 text-slate-400 hover:text-white"
              aria-label="Fechar menu"
            >
              <X className="size-5" />
            </button>
          </div>
        </div>
      )}

      <main className="lg:pl-64">
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
