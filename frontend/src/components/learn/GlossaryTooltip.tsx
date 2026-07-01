"use client";

import { useEffect, useRef, useState } from "react";
import { Info } from "lucide-react";
import { findTerm } from "@/lib/glossary";

interface Props {
  term: string;
  className?: string;
}

// 화면 곳곳의 숫자·용어 옆에 붙이는 맥락형 학습 툴팁(클릭식 — 모바일 호환).
export function GlossaryTooltip({ term, className = "" }: Props) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLSpanElement>(null);
  const entry = findTerm(term);

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  if (!entry) return null;

  return (
    <span ref={ref} className={`relative inline-flex ${className}`}>
      <button
        onClick={(e) => {
          e.stopPropagation();
          setOpen((v) => !v);
        }}
        aria-label={`${term} 설명 보기`}
        className="text-[#D1D5DB] hover:text-[#3182F6] transition-colors"
      >
        <Info size={12} />
      </button>
      {open && (
        <div className="absolute z-30 bottom-full left-1/2 -translate-x-1/2 mb-1.5 w-56 bg-[#191F28] text-white text-xs rounded-lg px-3 py-2 shadow-lg leading-relaxed">
          <p className="font-semibold mb-0.5">{entry.term}</p>
          <p className="text-[#D1D5DB]">{entry.short}</p>
          <div className="absolute top-full left-1/2 -translate-x-1/2 w-2 h-2 bg-[#191F28] rotate-45 -mt-1" />
        </div>
      )}
    </span>
  );
}
