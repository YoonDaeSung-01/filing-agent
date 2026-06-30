"use client";

import type { HistoryItem } from "@/hooks/useQueryHistory";

interface SidebarProps {
  history: HistoryItem[];
  onSelect: (item: HistoryItem) => void;
  onClear: () => void;
}

export function Sidebar({ history, onSelect, onClear }: SidebarProps) {
  return (
    <aside className="w-64 shrink-0 border-r border-border bg-white flex flex-col h-full">
      <div className="p-4 border-b border-border">
        <p className="text-xs font-semibold text-[#6B7280] uppercase tracking-wider">
          최근 질문
        </p>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-1">
        {history.length === 0 ? (
          <p className="text-xs text-[#6B7280] px-2 py-4 text-center">
            아직 질문 기록이 없어요
          </p>
        ) : (
          history.map((item) => (
            <button
              key={item.id}
              onClick={() => onSelect(item)}
              className="w-full text-left px-3 py-2.5 rounded-xl text-sm text-[#191F28] hover:bg-[#F2F4F6] transition-colors group"
            >
              <p className="truncate font-medium leading-snug">{item.question}</p>
              {item.company && (
                <p className="text-xs text-[#6B7280] mt-0.5 group-hover:text-[#3182F6]">
                  {item.company}
                  {item.year ? ` · ${item.year}년` : ""}
                </p>
              )}
            </button>
          ))
        )}
      </div>

      {history.length > 0 && (
        <div className="p-3 border-t border-border">
          <button
            onClick={onClear}
            className="w-full text-xs text-[#6B7280] hover:text-[#F04452] transition-colors py-1"
          >
            기록 지우기
          </button>
        </div>
      )}
    </aside>
  );
}
