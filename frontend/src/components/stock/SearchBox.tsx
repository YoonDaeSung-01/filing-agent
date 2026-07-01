"use client";

import { useEffect, useRef, useState } from "react";
import { Search } from "lucide-react";
import { searchStocks } from "@/lib/api";
import type { SearchResult } from "@/lib/types";

interface Props {
  company: string;
  onSelect: (name: string) => void;
}

export function SearchBox({ company, onSelect }: Props) {
  const [term, setTerm] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [open, setOpen] = useState(false);
  const boxRef = useRef<HTMLDivElement>(null);

  // 디바운스 검색
  useEffect(() => {
    if (!term.trim()) {
      setResults([]);
      return;
    }
    const t = setTimeout(async () => {
      setResults(await searchStocks(term));
    }, 250);
    return () => clearTimeout(t);
  }, [term]);

  // 바깥 클릭 시 닫기
  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  const pick = (name: string) => {
    onSelect(name);
    setTerm("");
    setResults([]);
    setOpen(false);
  };

  return (
    <div ref={boxRef} className="relative flex-1 min-w-[200px] max-w-sm">
      <div className="flex items-center gap-2 bg-white border border-border rounded-xl px-3 py-2.5 focus-within:ring-2 focus-within:ring-[#3182F6]">
        <Search size={16} className="text-[#9CA3AF] shrink-0" />
        <input
          value={term}
          onFocus={() => setOpen(true)}
          onChange={(e) => {
            setTerm(e.target.value);
            setOpen(true);
          }}
          placeholder={`종목 검색 (현재: ${company})`}
          className="flex-1 min-w-0 text-sm text-[#191F28] placeholder:text-[#9CA3AF] focus:outline-none"
        />
      </div>

      {open && results.length > 0 && (
        <ul className="absolute z-20 mt-1.5 w-full bg-white border border-border rounded-xl shadow-card-hover overflow-hidden max-h-72 overflow-y-auto">
          {results.map((r) => (
            <li key={r.ticker}>
              <button
                onClick={() => pick(r.name)}
                className="w-full flex items-center justify-between px-3 py-2.5 text-left hover:bg-[#EBF3FF] transition-colors"
              >
                <span className="text-sm font-medium text-[#191F28]">{r.name}</span>
                <span className="text-xs text-[#9CA3AF]">{r.ticker}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
      {open && term.trim() && results.length === 0 && (
        <div className="absolute z-20 mt-1.5 w-full bg-white border border-border rounded-xl shadow-card-hover px-3 py-2.5">
          <p className="text-xs text-[#9CA3AF]">
            검색 결과 없음 (공식 상장사명으로 검색 · 예: NAVER)
          </p>
        </div>
      )}
    </div>
  );
}
