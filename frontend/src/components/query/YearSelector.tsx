"use client";

import { TARGET_YEARS } from "@/lib/constants";

interface YearSelectorProps {
  value: number;
  onChange: (v: number) => void;
}

export function YearSelector({ value, onChange }: YearSelectorProps) {
  return (
    <div className="space-y-1.5">
      <label className="text-xs font-semibold text-[#6B7280] uppercase tracking-wider">
        연도
      </label>
      <div className="flex gap-1.5 bg-[#F2F4F6] p-1 rounded-xl">
        {TARGET_YEARS.map((y) => (
          <button
            key={y}
            onClick={() => onChange(y)}
            className={`flex-1 py-1.5 text-sm font-medium rounded-lg transition-all ${
              value === y
                ? "bg-white text-[#3182F6] shadow-sm font-semibold"
                : "text-[#6B7280] hover:text-[#191F28]"
            }`}
          >
            {y}
          </button>
        ))}
      </div>
    </div>
  );
}
