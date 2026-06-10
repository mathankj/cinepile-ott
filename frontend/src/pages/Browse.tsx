import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { catalog } from "../api";
import { TitleCard } from "../components/title/TitleCard";

/**
 * Browse page — filtered grid. Query params drive the filter set.
 * ?type=movie|series, ?genre=action, ?sort=-published_at, ?page=2
 */
export default function Browse() {
  const { t } = useTranslation();
  const [params, setParams] = useSearchParams();
  const filters = {
    type: (params.get("type") as "movie" | "series" | null) ?? undefined,
    genre: params.get("genre") ?? undefined,
    sort: params.get("sort") ?? "-published_at",
    page: Number(params.get("page") ?? "1"),
    page_size: 30,
  };

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ["titles", filters],
    queryFn: () => catalog.listTitles(filters),
    // Keep the previous page's results visible while a new query loads —
    // makes filter swaps feel instant instead of flashing to "Loading…"
    placeholderData: (prev) => prev,
    // Backend caches list responses for 60s; mirror that on the client so
    // back-nav from a title detail re-uses what we already have.
    staleTime: 60_000,
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
          {filters.type === "movie" ? t("nav.movies") : filters.type === "series" ? t("nav.tv_shows") : t("browse.title")}
        </h1>
        <div className="flex flex-wrap gap-2">
          <select
            value={filters.type ?? ""}
            onChange={(e) => setParam("type", e.target.value || null)}
            className="rounded border border-white/20 bg-[var(--color-bg-surface)] px-3 py-2 text-sm"
            aria-label={t("browse.filter_type")}
          >
            <option value="">{t("browse.all_types")}</option>
            <option value="movie">{t("nav.movies")}</option>
            <option value="series">{t("nav.tv_shows")}</option>
          </select>
          <select
            value={filters.genre || ""}
            onChange={(e) => setParam("genre", e.target.value || null)}
            className="rounded border border-white/20 bg-[var(--color-bg-surface)] px-3 py-2 text-sm"
            aria-label={t("browse.filter_genre")}
          >
            <option value="">{t("browse.all_genres")}</option>
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
            aria-label={t("browse.filter_sort")}
          >
            <option value="-published_at">{t("browse.sort_newest")}</option>
            <option value="published_at">{t("browse.sort_oldest")}</option>
            <option value="title">{t("browse.sort_az")}</option>
            <option value="-title">{t("browse.sort_za")}</option>
            <option value="-view_count">{t("browse.sort_most_watched")}</option>
          </select>
        </div>
      </header>

      {/* First-time load — shimmer grid replaces the bare "Loading…" text.
          Cold Neon round-trip is 5-30s; a skeleton makes the wait readable. */}
      {isLoading && (
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
          {[...Array(12)].map((_, i) => (
            <div key={i} className="skeleton-shimmer aspect-video rounded" />
          ))}
        </div>
      )}

      {data && data.items.length === 0 && (
        <div className="rounded border border-white/10 bg-[var(--color-bg-elevated)] p-8 text-center text-white/60">
          {t("browse.empty")}
        </div>
      )}

      {data && data.items.length > 0 && (
        <div
          className={`grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 transition-opacity duration-200 ${
            isFetching ? "opacity-60" : "opacity-100"
          }`}
        >
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
  const { t } = useTranslation();
  const totalPages = Math.ceil(total / pageSize);
  return (
    <div className="mt-8 flex items-center justify-center gap-2 text-sm">
      <button
        type="button"
        disabled={page <= 1}
        onClick={() => onPage(page - 1)}
        className="rounded border border-white/20 px-3 py-1.5 disabled:opacity-40"
      >
        {t("browse.prev")}
      </button>
      <span className="px-2 text-white/70">
        {t("browse.page_of", { page, total: totalPages })}
      </span>
      <button
        type="button"
        disabled={page >= totalPages}
        onClick={() => onPage(page + 1)}
        className="rounded border border-white/20 px-3 py-1.5 disabled:opacity-40"
      >
        {t("browse.next")}
      </button>
    </div>
  );
}
