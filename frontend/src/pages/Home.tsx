import { useQuery } from "@tanstack/react-query";
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
    staleTime: 60_000,
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
        {data.rows.map((row) => (
          <TitleRow key={row.kind} title={row.title} items={row.items} />
        ))}
      </div>
    </div>
  );
}

function HomeSkeleton() {
  return (
    <div className="animate-fade-in">
      <div className="h-[50vh] md:h-[85vh] bg-[var(--color-bg-elevated)]" />
      <div className="space-y-8 px-4 md:px-8 lg:px-[60px] py-8">
        {[...Array(4)].map((_, i) => (
          <div key={i}>
            <div className="mb-3 h-5 w-48 bg-[var(--color-bg-elevated)] rounded" />
            <div className="flex gap-1 overflow-hidden">
              {[...Array(6)].map((_, j) => (
                <div
                  key={j}
                  className="aspect-video flex-none rounded bg-[var(--color-bg-elevated)]"
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
