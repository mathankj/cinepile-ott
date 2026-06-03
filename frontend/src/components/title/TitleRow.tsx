import { useRef, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { TitleCard } from "./TitleCard";
import type { TitleSummary } from "../../api/types";

/**
 * Horizontal-scrolling row of title cards.
 * Desktop: arrow buttons appear on hover (Netflix pattern).
 * Mobile: scroll-snap horizontal pan, no arrows.
 *
 * Card widths by breakpoint match Netflix: 160 / 210 / 240 / 280 / 300 px.
 */
export function TitleRow({
  title,
  items,
  progressByTitleId,
}: {
  title: string;
  items: TitleSummary[];
  progressByTitleId?: Record<number, number>;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [hover, setHover] = useState(false);

  function scrollBy(direction: "left" | "right") {
    const el = ref.current;
    if (!el) return;
    const width = el.clientWidth * 0.85;
    el.scrollBy({ left: direction === "left" ? -width : width, behavior: "smooth" });
  }

  if (!items.length) return null;

  return (
    <section
      className="relative group/row mb-12"
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
    >
      <h2 className="mb-3 px-4 md:px-8 lg:px-[60px] text-[1.125rem] md:text-[1.4rem] font-medium text-[var(--color-text-secondary)]">
        {title}
      </h2>
      <div
        ref={ref}
        className="no-scrollbar flex gap-1 overflow-x-auto scroll-smooth snap-x snap-mandatory px-4 md:px-8 lg:px-[60px]"
      >
        {items.map((t) => (
          <div
            key={t.id}
            className="snap-start flex-none"
            style={{ width: "var(--card-w)" }}
          >
            <TitleCard
              title={t}
              progressPercent={progressByTitleId?.[t.id]}
            />
          </div>
        ))}
      </div>
      {/* Arrows — desktop only, on row hover */}
      {hover && (
        <>
          <button
            type="button"
            className="absolute left-0 top-1/2 -translate-y-1/2 hidden h-[calc(100%-2.5rem)] w-[60px] items-center justify-center bg-black/40 backdrop-blur-sm text-white opacity-0 transition-opacity duration-200 hover:bg-black/60 group-hover/row:opacity-100 md:flex"
            onClick={() => scrollBy("left")}
            aria-label="Scroll left"
          >
            <ChevronLeft size={32} />
          </button>
          <button
            type="button"
            className="absolute right-0 top-1/2 -translate-y-1/2 hidden h-[calc(100%-2.5rem)] w-[60px] items-center justify-center bg-black/40 backdrop-blur-sm text-white opacity-0 transition-opacity duration-200 hover:bg-black/60 group-hover/row:opacity-100 md:flex"
            onClick={() => scrollBy("right")}
            aria-label="Scroll right"
          >
            <ChevronRight size={32} />
          </button>
        </>
      )}
      <style>{`
        section { --card-w: 160px; }
        @media (min-width: 640px) { section { --card-w: 210px; } }
        @media (min-width: 1024px) { section { --card-w: 240px; } }
        @media (min-width: 1280px) { section { --card-w: 280px; } }
        @media (min-width: 1920px) { section { --card-w: 300px; } }
      `}</style>
    </section>
  );
}
