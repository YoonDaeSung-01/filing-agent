"use client";

import { QUICK_QUERIES } from "@/lib/constants";

const CATEGORY_COLORS = {
  lookup: "bg-[#EBF3FF] text-[#3182F6] hover:bg-[#3182F6] hover:text-white",
  change: "bg-[#FFF0F1] text-[#F04452] hover:bg-[#F04452] hover:text-white",
  doc:    "bg-[#F2F4F6] text-[#6B7280] hover:bg-[#191F28] hover:text-white",
  combine:"bg-[#F0FDF4] text-[#16A34A] hover:bg-[#16A34A] hover:text-white",
} as const;

interface QuickQueriesProps {
  company: string;
  year: number;
  onSelect: (question: string) => void;
}

export function QuickQueries({ company, year, onSelect }: QuickQueriesProps) {
  const target = company || "삼성전자";

  return (
    <div className="space-y-2">
      <p className="text-xs font-semibold text-[#6B7280] uppercase tracking-wider">
        빠른 질문
      </p>
      <div className="flex flex-wrap gap-2">
        {QUICK_QUERIES.map((q) => (
          <button
            key={q.label}
            onClick={() => onSelect(q.questionFn(target, year))}
            className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-all ${CATEGORY_COLORS[q.category]}`}
          >
            {q.label}
          </button>
        ))}
      </div>
    </div>
  );
}
