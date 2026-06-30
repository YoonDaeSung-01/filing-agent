"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";

function parseSource(raw: string): string {
  // "OpenDART fnlttSinglAcnt.json (corp_code=..., bsns_year=2024, ..., fs_div=CFS)"
  // → 사람이 읽는 형태로
  if (raw.startsWith("OpenDART")) {
    const yearMatch = raw.match(/bsns_year=(\d+)/);
    const fsMatch = raw.match(/fs_div=(\w+)/);
    const year = yearMatch?.[1] ?? "";
    const fs =
      fsMatch?.[1] === "CFS"
        ? "연결재무제표"
        : fsMatch?.[1] === "OFS"
          ? "별도재무제표"
          : "";
    const parts = ["OpenDART 전자공시", year && `${year}년 사업보고서`, fs].filter(Boolean);
    return parts.join(" · ");
  }
  return raw;
}

export function SourcePanel({ sources }: { sources: string[] }) {
  const [open, setOpen] = useState(false);

  if (sources.length === 0) return null;

  return (
    <div className="border-t border-border pt-3">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1.5 text-xs font-semibold text-[#6B7280] hover:text-[#3182F6] transition-colors"
      >
        {open ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
        출처 {sources.length}건
      </button>

      {open && (
        <ul className="mt-2 space-y-1.5">
          {sources.map((src, i) => (
            <li
              key={i}
              className="flex items-start gap-2 text-xs text-[#6B7280] bg-[#F2F4F6] px-3 py-2 rounded-xl"
            >
              <span className="text-[#3182F6] font-bold shrink-0">{i + 1}</span>
              <span>{parseSource(src)}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
