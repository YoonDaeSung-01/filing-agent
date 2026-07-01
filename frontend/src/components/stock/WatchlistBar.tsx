"use client";

import { X, Star } from "lucide-react";
import { useWatchlist } from "@/hooks/useWatchlist";

interface Props {
  activeCompany: string;
  onSelect: (name: string) => void;
}

export function WatchlistBar({ activeCompany, onSelect }: Props) {
  const { items, remove } = useWatchlist();

  if (items.length === 0) {
    return (
      <div className="flex items-center gap-1.5 text-xs text-[#9CA3AF] px-1">
        <Star size={13} />
        관심종목이 없어요 — 종목 카드의 별 아이콘을 눌러 추가하세요
      </div>
    );
  }

  return (
    <div className="flex flex-wrap gap-1.5">
      {items.map((it) => {
        const active = it.name === activeCompany;
        return (
          <div
            key={it.name}
            role="button"
            tabIndex={0}
            onClick={() => onSelect(it.name)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") onSelect(it.name);
            }}
            className={[
              "group flex items-center gap-1.5 pl-3 pr-2 py-1.5 rounded-full text-xs font-medium transition-colors border cursor-pointer",
              active
                ? "bg-[#3182F6] text-white border-[#3182F6]"
                : "bg-white text-[#191F28] border-border hover:border-[#3182F6]",
            ].join(" ")}
          >
            {it.name}
            <button
              type="button"
              aria-label={`${it.name} 관심종목에서 제거`}
              onClick={(e) => {
                e.stopPropagation();
                remove(it.name);
              }}
              className={[
                "rounded-full p-0.5 transition-colors",
                active ? "hover:bg-white/20" : "hover:bg-[#F2F4F6]",
              ].join(" ")}
            >
              <X size={11} />
            </button>
          </div>
        );
      })}
    </div>
  );
}
