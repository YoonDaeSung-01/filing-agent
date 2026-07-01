"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";
import type { GlossaryTerm } from "@/lib/glossary";

const CATEGORY_STYLE: Record<string, { bg: string; text: string }> = {
  기초: { bg: "#EBF3FF", text: "#3182F6" },
  거래: { bg: "#F0FDF4", text: "#16A34A" },
  재무: { bg: "#FFF7ED", text: "#EA580C" },
  모의투자: { bg: "#F5F3FF", text: "#7C3AED" },
};

export function TermCard({ term }: { term: GlossaryTerm }) {
  const [open, setOpen] = useState(false);
  const style = CATEGORY_STYLE[term.category] ?? { bg: "#F2F4F6", text: "#6B7280" };

  return (
    <div className="bg-white rounded-2xl border border-border shadow-card overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full text-left p-5 flex items-start justify-between gap-3"
      >
        <div className="min-w-0">
          <div className="flex items-center gap-2 mb-1.5">
            <span
              className="text-[10px] font-bold px-2 py-0.5 rounded-full"
              style={{ background: style.bg, color: style.text }}
            >
              {term.category}
            </span>
          </div>
          <p className="text-[15px] font-bold text-[#191F28]">{term.term}</p>
          <p className="text-xs text-[#6B7280] mt-1 leading-relaxed">{term.short}</p>
        </div>
        <ChevronDown
          size={16}
          className={`shrink-0 mt-1 text-[#D1D5DB] transition-transform ${open ? "rotate-180" : ""}`}
        />
      </button>

      {open && (
        <div className="px-5 pb-5 pt-0 -mt-1">
          <div className="h-px bg-[#F2F4F6] mb-3" />
          <p className="text-sm text-[#191F28] leading-relaxed">{term.long}</p>
        </div>
      )}
    </div>
  );
}
