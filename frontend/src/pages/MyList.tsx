import { useQuery } from "@tanstack/react-query";
import { me } from "../api";
import { TitleCard } from "../components/title/TitleCard";

export default function MyList() {
  const { data, isLoading } = useQuery({
    queryKey: ["watchlist"],
    queryFn: () => me.listWatchlist(),
  });
  return (
    <div className="px-4 md:px-8 lg:px-[60px] py-12">
      <h1 className="mb-8 text-[2rem] font-bold">My List</h1>
      {isLoading && <div className="text-white/60">Loading…</div>}
      {!isLoading && data?.items.length === 0 && (
        <div className="rounded border border-white/10 bg-[var(--color-bg-elevated)] p-8 text-center text-white/60">
          Your list is empty. Add titles from any title page.
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
