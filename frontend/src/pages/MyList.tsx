import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Bookmark } from "lucide-react";
import { useTranslation } from "react-i18next";
import { me } from "../api";
import { TitleCard } from "../components/title/TitleCard";

export default function MyList() {
  const { t } = useTranslation();
  const { data, isLoading } = useQuery({
    queryKey: ["watchlist"],
    queryFn: () => me.listWatchlist(),
  });
  return (
    <div className="px-4 md:px-8 lg:px-[60px] py-12">
      <h1 className="mb-8 text-[2rem] font-bold">{t("nav.my_list")}</h1>

      {/* Shimmer skeleton while loading so the page doesn't look broken on
          a cold-Neon round trip (can take 5+ seconds on the first request). */}
      {isLoading && (
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="skeleton-shimmer aspect-video rounded" />
          ))}
        </div>
      )}

      {!isLoading && data?.items.length === 0 && (
        <div className="rounded border border-white/10 bg-[var(--color-bg-elevated)] p-10 text-center">
          <Bookmark size={40} className="mx-auto mb-4 text-white/40" />
          <h2 className="text-lg font-semibold text-white">{t("my_list.empty_title")}</h2>
          <p className="mx-auto mt-2 max-w-md text-sm text-white/60">
            {t("my_list.empty_hint_prefix")} <span className="inline-flex h-5 w-5 items-center justify-center rounded-full border border-white/60 align-text-bottom">+</span> {t("my_list.empty_hint_suffix")}
          </p>
          <Link to="/browse" className="btn-primary mt-6 inline-flex">
            {t("my_list.browse_catalog")}
          </Link>
        </div>
      )}
      {data && data.items.length > 0 && (
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
          {data.items.map((w) => (
            <TitleCard key={w.title.id} title={w.title} />
          ))}
        </div>
      )}
    </div>
  );
}
