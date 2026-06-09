import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { catalog } from "../api";
import { TitleCard } from "../components/title/TitleCard";
import { Search as SearchIcon } from "lucide-react";

export default function Search() {
  const [params, setParams] = useSearchParams();
  // Seed from URL — if the user lands here from a back-nav (or bookmark),
  // the input pre-populates with whatever was in ?q=. Also fires the
  // debounced effect below so results render on first paint.
  const [q, setQ] = useState(params.get("q") ?? "");

  // Debounce 300ms before firing the query
  const [debounced, setDebounced] = useState(q.trim());
  useEffect(() => {
    const t = setTimeout(() => setDebounced(q.trim()), 300);
    return () => clearTimeout(t);
  }, [q]);

  // Keep URL in sync with the debounced query. Two behaviours that matter:
  //  1) Only write to URL when query is 2+ chars (matches the API's min-length
  //     guard). Single-char inputs would otherwise leave a `?q=b` in history
  //     that re-renders as "Type at least 2 characters" — stale state.
  //  2) `replace: true` so each keystroke doesn't push a new history entry.
  //     The original /search entry IS preserved as the back-target; only its
  //     URL changes. Clicking a result then pushes /title/X normally, so
  //     back from /title/X correctly returns to /search?q=bunny.
  useEffect(() => {
    const current = params.get("q") ?? "";
    if (debounced.length >= 2) {
      if (current !== debounced) setParams({ q: debounced }, { replace: true });
    } else if (current) {
      setParams({}, { replace: true });
    }
  }, [debounced, params, setParams]);

  const { data, isFetching } = useQuery({
    queryKey: ["search", debounced],
    queryFn: () => catalog.search(debounced),
    enabled: debounced.length >= 2,
    staleTime: 30_000,
    // Keep showing the previous results while the next keystroke's query is
    // in flight — without this every keystroke flashes the grid away and
    // back, which reads as flicker.
    placeholderData: (prev) => prev,
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
        {debounced.length >= 2 && isFetching && !data && (
          <p className="text-white/50">Searching…</p>
        )}
        {debounced.length >= 2 && data && data.length === 0 && !isFetching && (
          <p className="text-white/50">No matches for "{debounced}".</p>
        )}
        {debounced.length >= 2 && data && data.length > 0 && (
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
