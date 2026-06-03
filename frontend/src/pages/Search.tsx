import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { catalog } from "../api";
import { TitleCard } from "../components/title/TitleCard";
import { Search as SearchIcon } from "lucide-react";

export default function Search() {
  const [params, setParams] = useSearchParams();
  const [q, setQ] = useState(params.get("q") ?? "");

  // Debounce 300ms before firing the query
  const [debounced, setDebounced] = useState(q);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(q.trim()), 300);
    return () => clearTimeout(t);
  }, [q]);

  useEffect(() => {
    if (debounced) setParams({ q: debounced }, { replace: true });
    else setParams({}, { replace: true });
  }, [debounced, setParams]);

  const { data, isFetching } = useQuery({
    queryKey: ["search", debounced],
    queryFn: () => catalog.search(debounced),
    enabled: debounced.length >= 2,
    staleTime: 30_000,
  });

  return (
    <div className="px-4 md:px-8 lg:px-[60px] py-12">
      <h1 className="mb-6 text-[2rem] font-bold">Search</h1>
      <div className="relative max-w-xl">
        <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 text-white/50" size={20} />
        <input
          type="search"
          autoFocus
          placeholder="Titles, genres, languages…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          className="input-base !pl-10"
        />
      </div>

      <div className="mt-8">
        {debounced.length < 2 && (
          <p className="text-white/50">Type at least 2 characters.</p>
        )}
        {debounced.length >= 2 && isFetching && (
          <p className="text-white/50">Searching…</p>
        )}
        {data && data.length === 0 && !isFetching && (
          <p className="text-white/50">No matches for "{debounced}".</p>
        )}
        {data && data.length > 0 && (
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
            {data.map((t) => (
              <TitleCard key={t.id} title={t} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
