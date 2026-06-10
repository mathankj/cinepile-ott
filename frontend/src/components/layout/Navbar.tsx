import { useEffect, useState } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { Search, Bell, ChevronDown, Globe, Menu, X } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useAuthStore } from "../../stores/auth";
import { useProfileStore } from "../../stores/profile";
import { LANGUAGES } from "../../i18n";
import { Avatar } from "../Avatar";

/**
 * Top navigation — transparent over hero, fades to solid #141414 on scroll > 60px.
 * Mobile collapses to a "Browse" dropdown / hamburger.
 *
 * Netflix conventions baked in:
 * - Logo + nav left-aligned (NOT centered)
 * - Active link bold, inactive normal weight
 * - 68px desktop / 48px mobile height
 * - Sticky, NOT auto-hide on scroll
 */
export default function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const { user, isLoggedIn, clear } = useAuthStore();
  const nav = useNavigate();
  const { t } = useTranslation();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 60);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const navLinks = [
    { to: "/", label: t("nav.home") },
    { to: "/browse?type=series", label: t("nav.tv_shows") },
    { to: "/browse?type=movie", label: t("nav.movies") },
    { to: "/browse?sort=-published_at", label: t("nav.new_and_popular") },
    { to: "/me/list", label: t("nav.my_list"), authOnly: true },
  ];

  return (
    <>
      <header
        className={`fixed inset-x-0 top-0 z-50 h-[48px] md:h-[68px] transition-colors duration-300 ${
          scrolled ? "bg-[var(--color-bg)]" : "navbar-fade"
        }`}
      >
        <div className="flex h-full items-center px-4 md:px-8 lg:px-[60px]">
          {/* Logo */}
          <Link to="/" className="mr-6 md:mr-9 flex items-center" aria-label={t("nav.brand_home")}>
            <span className="text-[1.4rem] md:text-[1.6rem] font-extrabold tracking-tight text-[var(--color-brand)]">
              CINEPILE
            </span>
          </Link>

          {/* Desktop nav — gated on lg: (1024px+) instead of md: (768px+) because
              at iPad-portrait (768) the 5 nav links + brand wrapped to two lines.
              Tablets now also see the hamburger drawer. */}
          <nav className="hidden lg:flex items-center gap-[20px] text-[14px] text-[var(--color-text-secondary)]">
            {navLinks
              .filter((l) => !l.authOnly || isLoggedIn())
              .map((l) => (
                <NavLink
                  key={l.to}
                  to={l.to}
                  className={({ isActive }) =>
                    `transition-colors hover:text-[var(--color-text-muted)] ${
                      isActive ? "font-bold text-white" : "font-normal"
                    }`
                  }
                  end={l.to === "/"}
                >
                  {l.label}
                </NavLink>
              ))}
          </nav>

          {/* Hamburger — shown below lg so tablets get the drawer too. */}
          <button
            type="button"
            className="lg:hidden ml-auto p-2 text-[var(--color-text-secondary)]"
            onClick={() => setDrawerOpen(true)}
            aria-label={t("nav.open_menu")}
          >
            <Menu size={22} />
          </button>

          {/* Right cluster — also lg+. */}
          <div className="ml-auto hidden lg:flex items-center gap-[22px] text-[var(--color-text-secondary)]">
            <button
              type="button"
              onClick={() => nav("/search")}
              className="hover:text-white"
              aria-label={t("nav.search")}
            >
              <Search size={22} />
            </button>
            <button type="button" className="hover:text-white" aria-label={t("nav.notifications")}>
              <Bell size={22} />
            </button>
            <LanguagePicker />
            {isLoggedIn() ? (
              <ProfileMenu user={user} onLogout={clear} />
            ) : (
              <Link to="/login" className="btn-primary !py-[6px] !px-4 text-sm">
                {t("nav.sign_in")}
              </Link>
            )}
          </div>
        </div>
      </header>

      {/* Mobile + tablet drawer */}
      {drawerOpen && (
        <div className="fixed inset-0 z-[60] lg:hidden">
          <div
            className="absolute inset-0 bg-black/70 animate-fade-in"
            onClick={() => setDrawerOpen(false)}
          />
          <aside className="absolute right-0 top-0 h-full w-[280px] bg-[var(--color-bg)] border-l border-white/10 p-6 animate-slide-in-right">
            <button
              type="button"
              className="mb-6 text-white"
              onClick={() => setDrawerOpen(false)}
              aria-label={t("nav.close_menu")}
            >
              <X size={24} />
            </button>
            <nav className="flex flex-col gap-4 text-[16px] text-white">
              {navLinks
                .filter((l) => !l.authOnly || isLoggedIn())
                .map((l) => (
                  <Link
                    key={l.to}
                    to={l.to}
                    onClick={() => setDrawerOpen(false)}
                    className="hover:text-[var(--color-text-muted)]"
                  >
                    {l.label}
                  </Link>
                ))}
              <Link
                to="/search"
                onClick={() => setDrawerOpen(false)}
                className="flex items-center gap-2 hover:text-[var(--color-text-muted)]"
              >
                <Search size={18} /> Search
              </Link>
              <div className="my-2 h-px bg-white/10" />
              {isLoggedIn() ? (
                <>
                  <Link to="/me/list" onClick={() => setDrawerOpen(false)}>
                    My List
                  </Link>
                  <Link to="/me/history" onClick={() => setDrawerOpen(false)}>
                    History
                  </Link>
                  <Link to="/subscribe" onClick={() => setDrawerOpen(false)}>
                    Subscription
                  </Link>
                  <Link to="/account" onClick={() => setDrawerOpen(false)}>
                    Account
                  </Link>
                  {(user?.role === "admin" || user?.role === "content_manager") && (
                    <Link to="/admin" onClick={() => setDrawerOpen(false)} className="text-[var(--color-brand)]">
                      Admin
                    </Link>
                  )}
                  <button
                    type="button"
                    className="text-left text-[var(--color-text-muted)]"
                    onClick={() => {
                      clear();
                      setDrawerOpen(false);
                      nav("/");
                    }}
                  >
                    Sign out
                  </button>
                </>
              ) : (
                <Link to="/login" onClick={() => setDrawerOpen(false)} className="btn-primary">
                  Sign In
                </Link>
              )}
            </nav>
          </aside>
        </div>
      )}
    </>
  );
}

/**
 * Tiny language picker — globe icon opens a popover with EN / HI / TA. The
 * selected language is stored in localStorage by i18next-browser-languagedetector,
 * so it survives reloads automatically.
 */
function LanguagePicker() {
  const [open, setOpen] = useState(false);
  const { t, i18n } = useTranslation();
  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="hover:text-white"
        aria-label={t("nav.language")}
        aria-expanded={open}
      >
        <Globe size={20} />
      </button>
      {open && (
        <div className="absolute right-0 mt-2 w-44 rounded bg-black/90 backdrop-blur-md border border-white/10 py-1 text-sm animate-slide-up">
          {LANGUAGES.map((l) => (
            <button
              key={l.code}
              type="button"
              onClick={() => {
                void i18n.changeLanguage(l.code);
                setOpen(false);
              }}
              className={`block w-full px-3 py-2 text-left hover:bg-white/10 ${
                i18n.resolvedLanguage === l.code ? "text-white" : "text-white/70"
              }`}
            >
              {l.nativeName}
              <span className="ml-2 text-[11px] text-white/40">{l.code.toUpperCase()}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function ProfileMenu({
  user,
  onLogout,
}: {
  user: { full_name: string | null; email: string; role: string } | null;
  onLogout: () => void;
}) {
  const [open, setOpen] = useState(false);
  const nav = useNavigate();
  const { t } = useTranslation();
  const activeProfile = useProfileStore((s) => s.active);
  const clearProfile = useProfileStore((s) => s.clear);
  if (!user) return null;
  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2"
        aria-label={t("nav.account_menu")}
      >
        <Avatar value={activeProfile?.avatar} size="xs" alt={activeProfile?.name ?? user.email} />
        <ChevronDown size={14} className="text-white/70" />
      </button>
      {open && (
        <div className="absolute right-0 mt-2 w-60 rounded bg-black/90 backdrop-blur-md border border-white/10 py-2 text-sm animate-slide-up">
          {activeProfile && (
            <div className="px-3 py-2 border-b border-white/10">
              <div className="flex items-center gap-2">
                <Avatar value={activeProfile.avatar} size="sm" alt={activeProfile.name} />
                <div>
                  <div className="font-medium text-white">{activeProfile.name}</div>
                  <div className="text-[11px] text-white/60">{user.email}</div>
                </div>
              </div>
            </div>
          )}
          <button
            type="button"
            onClick={() => {
              clearProfile();
              setOpen(false);
              nav("/profiles");
            }}
            className="block w-full px-3 py-2 text-left hover:bg-white/5"
          >
            {t("nav.switch_profile")}
          </button>
          <Link
            to="/me/list"
            onClick={() => setOpen(false)}
            className="block px-3 py-2 hover:bg-white/5"
          >
            {t("nav.my_list")}
          </Link>
          <Link
            to="/me/history"
            onClick={() => setOpen(false)}
            className="block px-3 py-2 hover:bg-white/5"
          >
            {t("nav.viewing_history")}
          </Link>
          <Link
            to="/subscribe"
            onClick={() => setOpen(false)}
            className="block px-3 py-2 hover:bg-white/5"
          >
            {t("nav.subscription")}
          </Link>
          <Link
            to="/account"
            onClick={() => setOpen(false)}
            className="block px-3 py-2 hover:bg-white/5"
          >
            Account
          </Link>
          {(user.role === "admin" || user.role === "content_manager") && (
            <Link
              to="/admin"
              onClick={() => setOpen(false)}
              className="block px-3 py-2 text-[var(--color-brand)] hover:bg-white/5"
            >
              {t("nav.admin")}
            </Link>
          )}
          <div className="my-1 h-px bg-white/10" />
          <button
            type="button"
            className="block w-full px-3 py-2 text-left hover:bg-white/5"
            onClick={() => {
              onLogout();
              setOpen(false);
              nav("/");
            }}
          >
            {t("nav.sign_out")}
          </button>
        </div>
      )}
    </div>
  );
}
