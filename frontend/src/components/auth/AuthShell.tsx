import { motion } from "framer-motion";
import { Link } from "react-router-dom";

/**
 * Netflix-style auth shell: full-bleed dark hero photo + scrim, a fixed black
 * top bar with just the brand mark (no nav), and a centered glass card for
 * the form. The hero image is a static picsum seed so it loads from CDN with
 * no extra dependency; swap to a brand asset later.
 *
 * Why one shell, two pages: login and signup share 90% of layout, and the
 * scrim+image needs to stay in place during the cross-route transition so it
 * doesn't flash. We keep all that in here; the pages own the form fields.
 */
export default function AuthShell({
  title,
  children,
  footer,
}: {
  title: string;
  children: React.ReactNode;
  footer: React.ReactNode;
}) {
  return (
    <div className="relative min-h-screen w-full overflow-hidden bg-black">
      {/* Background — large landscape image with heavy dark overlay so foreground
          text is always WCAG-AA legible regardless of which picsum seed loads. */}
      <img
        src="https://picsum.photos/seed/anjaneya-auth-hero/1920/1080"
        alt=""
        aria-hidden="true"
        className="absolute inset-0 h-full w-full object-cover opacity-50"
      />
      <div
        className="absolute inset-0"
        style={{
          background:
            "linear-gradient(180deg, rgba(0,0,0,0.7) 0%, rgba(0,0,0,0.6) 50%, rgba(0,0,0,0.9) 100%)",
        }}
      />

      {/* Top bar — only the brand. No nav, no profile menu. */}
      <header className="relative z-10 px-4 md:px-8 lg:px-[60px] py-5">
        <Link to="/" aria-label="Anjaneya home" className="inline-block">
          <span className="text-[1.6rem] md:text-[2rem] font-extrabold tracking-tight text-[var(--color-brand)]">
            ANJANEYA
          </span>
        </Link>
      </header>

      {/* Centered card */}
      <main className="relative z-10 grid min-h-[calc(100vh-120px)] place-items-center px-4 pb-16">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, ease: [0.5, 0, 0.1, 1] }}
          className="w-full max-w-[450px] rounded-md bg-black/75 px-8 py-10 md:px-16 md:py-14 backdrop-blur-sm"
        >
          <h1 className="mb-7 text-[2rem] font-bold text-white">{title}</h1>
          {children}
          <div className="mt-12 text-[15px] text-white/70">{footer}</div>
          <p className="mt-4 text-[13px] text-white/50">
            This page uses cookies and stores tokens locally to keep you signed in. By continuing
            you accept our terms.
          </p>
        </motion.div>
      </main>
    </div>
  );
}
