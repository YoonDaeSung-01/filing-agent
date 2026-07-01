"use client";

import { useMemo, useState } from "react";
import { Header } from "@/components/layout/Header";
import { GLOSSARY, type GlossaryCategory } from "@/lib/glossary";

const CATEGORIES: (GlossaryCategory | "전체")[] = ["전체", "기초", "거래", "재무", "모의투자"];

export default function LearnPage() {
  const [category, setCategory] = useState<(typeof CATEGORIES)[number]>("전체");
  const [q, setQ] = useState("");

  const filtered = useMemo(() => {
    return GLOSSARY.filter((g) => {
      if (category !== "전체" && g.category !== category) return false;
      if (q.trim() && !g.term.includes(q.trim()) && !g.short.includes(q.trim())) return false;
      return true;
    });
  }, [category, q]);

  return (
    <div className="flex flex-col h-screen">
      <Header />

      <main className="flex-1 overflow-y-auto p-4 md:p-6 bg-[#F9FAFB]">
        <div className="max-w-3xl mx-auto space-y-5">
          {/* 온보딩 안내 */}
          <div className="bg-white rounded-2xl p-5 shadow-card border border-border">
            <p className="text-sm font-bold text-[#191F28] mb-1">📚 처음이신가요?</p>
            <p className="text-xs text-[#6B7280] leading-relaxed">
              이 플랫폼은 투자 추천을 하지 않습니다. 대신 공시·재무·시세 등{" "}
              <strong className="text-[#191F28]">사실을 정확히 보여주고</strong>, 아래 용어를
              통해 스스로 판단하는 데 필요한 기초를 제공합니다. 모의투자로 먼저 연습하고,
              매매일지로 자신의 판단을 복기해 보세요.
            </p>
          </div>

          {/* 검색 + 카테고리 필터 */}
          <div className="space-y-3">
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="용어 검색 (예: 지정가, 매출액)"
              className="w-full text-sm bg-white border border-border rounded-xl px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-[#3182F6]"
            />
            <div className="flex flex-wrap gap-1.5">
              {CATEGORIES.map((c) => (
                <button
                  key={c}
                  onClick={() => setCategory(c)}
                  className={[
                    "px-3 py-1.5 text-xs font-semibold rounded-full transition-colors",
                    category === c
                      ? "bg-[#3182F6] text-white"
                      : "bg-white border border-border text-[#6B7280] hover:text-[#191F28]",
                  ].join(" ")}
                >
                  {c}
                </button>
              ))}
            </div>
          </div>

          {/* 용어 카드 */}
          {filtered.length === 0 ? (
            <p className="text-sm text-[#9CA3AF] text-center py-10">검색 결과가 없습니다.</p>
          ) : (
            <div className="space-y-3">
              {filtered.map((g) => (
                <div
                  key={g.term}
                  className="bg-white rounded-2xl p-5 shadow-card border border-border"
                >
                  <div className="flex items-center gap-2 mb-1.5">
                    <p className="text-sm font-bold text-[#191F28]">{g.term}</p>
                    <span className="text-[10px] font-semibold text-[#3182F6] bg-[#EBF3FF] px-2 py-0.5 rounded-full">
                      {g.category}
                    </span>
                  </div>
                  <p className="text-xs text-[#6B7280] mb-2">{g.short}</p>
                  <p className="text-sm text-[#191F28] leading-relaxed">{g.long}</p>
                </div>
              ))}
            </div>
          )}

          <p className="text-xs text-center text-[#9CA3AF] pt-2">
            본 용어 설명은 일반적인 개념·사실 안내이며, 특정 종목이나 투자 전략을
            추천하지 않습니다.
          </p>
        </div>
      </main>
    </div>
  );
}
