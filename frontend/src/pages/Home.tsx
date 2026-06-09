import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { home } from "../api";
import { Billboard } from "../components/title/Billboard";
import { TitleRow } from "../components/title/TitleRow";

/**
 * Home page — billboard hero + a stack of TitleRows from /v1/home.
 * Empty rows are filtered out by the backend.
 */
export default function Home() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["home"],
    queryFn: () => home.get("IN"),
    // Inherits 5min staleTime / 30min gcTime from QueryClient. placeholderData
    // keeps the previous payload on re-mount so navigating back never flashes
    // the skeleton — the user sees the old home instantly while a background
    // refresh runs (if stale).
    placeholderData: (prev) => prev,
  });

  // Hero selection: prefer the first title across all rows that has a
  // backdrop_url; fall back to the first title overall if none have art.
  // Avoids a flat-black hero when the top row's first item lacks art.
  const hero = (() => {
    if (!data?.rows.length) return null;
    for (const r of data.rows) {
      for (const t of r.items) {
        if (t.backdrop_url) return t;
      }
    }
    return data.rows[0]?.items[0] ?? null;
  })();

  if (isLoading) {
    return <HomeSkeleton />;
  }

  if (error || !data) {
    return (
      <div className="flex h-[80vh] items-center justify-center px-4">
        <p className="text-white/60">Couldn't load home page. Refresh to retry.</p>
      </div>
    );
  }

  return (
    <div>
      <Billboard title={hero} />
      <div className="-mt-16 md:-mt-24 relative z-10 pb-16">
        {data.rows.map((row, i) => (
          <motion.div
            key={row.kind}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.15 + i * 0.08, ease: [0.5, 0, 0.1, 1] }}
          >
            <TitleRow title={row.title} items={row.items} />
          </motion.div>
        ))}
      </div>
    </div>
  );
}

function HomeSkeleton() {
  return (
    <div className="animate-fade-in">
      <div className="skeleton-shimmer h-[50vh] md:h-[85vh]" />
      <div className="space-y-8 px-4 md:px-8 lg:px-[60px] py-8">
        {[...Array(4)].map((_, i) => (
          <div key={i}>
            <div className="skeleton-shimmer mb-3 h-5 w-48 rounded" />
            <div className="flex gap-1 overflow-hidden">
              {[...Array(6)].map((_, j) => (
                <div
                  key={j}
                  className="skeleton-shimmer aspect-video flex-none rounded"
                  style={{ width: 240 }}
                />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
