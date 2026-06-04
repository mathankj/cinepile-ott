import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { catalog } from "../api";
import { TitleCard } from "../components/title/TitleCard";

/**
 * Browse page — filtered grid. Query params drive the filter set.
 * ?type=movie|series, ?genre=action, ?sort=-published_at, ?page=2
 */
export default function Browse() {
  const [params, setParams] = useSearchParams();
  const filters = {
    type: (params.get("type") as "movie" | "series" | null) ?? undefined,
    genre: params.get("genre") ?? undefined,
    sort: params.get("sort") ?? "-published_at",
    page: Number(params.get("page") ?? "1"),
    page_size: 30,
  };

  const { data, isLoading } = useQuery({
    queryKey: ["titles", filters],
    queryFn: () => catalog.listTitles(filters),
    placeholderData: (prev) => prev,
  });

  const genresQ = useQuery({
    queryKey: ["genres"],
    queryFn: () => catalog.genres(),
    staleTime: 600_000,
  });

  function setParam(key: string, value: string | null) {
    const next = new URLSearchParams(params);
    if (!value) next.delete(key);
    else next.set(key, value);
    next.set("page", "1");
    setParams(next);
  }

  return (
    <div className="px-4 md:px-8 lg:px-[60px] py-12">
      <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <h1 className="text-[2rem] font-bold">
          {filters.type === "movie" ? "Movies" : filters.type === "series" ? "TV Shows" : "Browse"}
        </h1>
        <div className="flex flex-wrap gap-2">
          <select
            value={filters.type ?? ""}
            onChange={(e) => setParam("type", e.target.value || null)}
            className="rounded border border-white/20 bg-[var(--color-bg-surface)] px-3 py-2 text-sm"
            aria-label="Title type"
          >
            <option value="">All types</option>
            <option value="movie">Movies</option>
            <option value="series">TV Shows</option>
          </select>
          <select
            value={filters.genre || ""}
            onChange={(e) => setParam("genre", e.target.value || null)}
            className="rounded border border-white/20 bg-[var(--color-bg-surface)] px-3 py-2 text-sm"
            aria-label="Genre"
          >
            <option value="">All genres</option>
            {genresQ.data?.map((g) => (
              <option key={g.id} value={g.slug}>
                {g.name}
              </option>
            ))}
          </select>
          <select
            value={filters.sort}
            onChange={(e) => setParam("sort", e.target.value)}
            className="rounded border border-white/20 bg-[var(--color-bg-surface)] px-3 py-2 text-sm"
            aria-label="Sort"
          >
            <option value="-published_at">Newest first</option>
            <option value="published_at">Oldest first</option>
            <option value="title">A → Z</option>
            <option value="-title">Z → A</option>
            <option value="-view_count">Most watched</option>
          </select>
        </div>
      </header>

      {isLoading && <div className="text-white/60">Loading…</div>}

      {data && data.items.length === 0 && (
        <div className="rounded border border-white/10 bg-[var(--color-bg-elevated)] p-8 text-center text-white/60">
          No titles match. Try clearing filters.
        </div>
      )}

      {data && (
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
          {data.items.map((t) => (
            <TitleCard key={t.id} title={t} />
          ))}
        </div>
      )}

      {data && data.total > data.page_size && (
        <Pager
          page={data.page}
          pageSize={data.page_size}
          total={data.total}
          onPage={(p) => setParam("page", String(p))}
        />
      )}
    </div>
  );
}

function Pager({
  page,
  pageSize,
  total,
  onPage,
}: {
  page: number;
  pageSize: number;
  total: number;
  onPage: (p: number) => void;
}) {
  const totalPages = Math.ceil(total / pageSize);
  return (
    <div className="mt-8 flex items-center justify-center gap-2 text-sm">
      <button
        type="button"
        disabled={page <= 1}
        onClick={() => onPage(page - 1)}
        className="rounded border border-white/20 px-3 py-1.5 disabled:opacity-40"
      >
        Prev
      </button>
      <span className="px-2 text-white/70">
        Page {page} of {totalPages}
      </span>
      <button
        type="button"
        disabled={page >= totalPages}
        onClick={() => onPage(page + 1)}
        className="rounded border border-white/20 px-3 py-1.5 disabled:opacity-40"
      >
        Next
      </button>
    </div>
  );
}
