"use client";

import { useMemo, useState } from "react";
import { Search, BookOpen, ArrowLeftRight, Calculator, Wallet } from "lucide-react";
import { Header } from "@/components/layout/Header";
import { TermCard } from "@/components/learn/TermCard";
import { GLOSSARY, type GlossaryCategory } from "@/lib/glossary";

const CATEGORY_META: Record<
  GlossaryCategory,
  { icon: typeof BookOpen; color: string; bg: string }
> = {
  기초: { icon: BookOpen, color: "#3182F6", bg: "#EBF3FF" },
  거래: { icon: ArrowLeftRight, color: "#16A34A", bg: "#F0FDF4" },
  재무: { icon: Calculator, color: "#EA580C", bg: "#FFF7ED" },
  모의투자: { icon: Wallet, color: "#7C3AED", bg: "#F5F3FF" },
};

const CATEGORIES: GlossaryCategory[] = ["기초", "거래", "재무", "모의투자"];

export default function LearnPage() {
  const [category, setCategory] = useState<GlossaryCategory | "전체">("전체");
  const [q, setQ] = useState("");

  const filtered = useMemo(() => {
    return GLOSSARY.filter((g) => {
      if (category !== "전체" && g.category !== category) return false;
      if (q.trim() && !g.term.includes(q.trim()) && !g.short.includes(q.trim())) return false;
      return true;
    });
  }, [category, q]);

  const countByCategory = (c: GlossaryCategory) => GLOSSARY.filter((g) => g.category === c).length;

  return (
    <div className="flex flex-col h-screen">
      <Header />

      <main className="flex-1 overflow-y-auto bg-[#F9FAFB]">
        {/* 히어로 */}
        <div className="bg-gradient-to-b from-[#EBF3FF] to-[#F9FAFB] px-4 md:px-6 pt-8 pb-6">
          <div className="max-w-4xl mx-auto">
            <p className="text-2xl font-bold text-[#191F28] mb-2">투자 용어, 쉽게 배우기</p>
            <p className="text-sm text-[#6B7280] leading-relaxed max-w-lg">
              이 플랫폼은 투자를 추천하지 않습니다. 대신 공시·재무·시세 사실을 정확히
              보여드리고, 스스로 판단하는 데 필요한 기초를 여기서 익힐 수 있어요.
            </p>

            {/* 검색 */}
            <div className="mt-5 relative max-w-md">
              <Search
                size={16}
                className="absolute left-4 top-1/2 -translate-y-1/2 text-[#9CA3AF]"
              />
              <input
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="용어 검색 (예: 지정가, 매출액)"
                className="w-full text-sm bg-white border border-border rounded-xl pl-11 pr-4 py-3 shadow-card focus:outline-none focus:ring-2 focus:ring-[#3182F6]"
              />
            </div>
          </div>
        </div>

        <div className="max-w-4xl mx-auto p-4 md:p-6 space-y-5">
          {/* 카테고리 카드 */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5">
            <button
              onClick={() => setCategory("전체")}
              className={[
                "rounded-2xl p-3.5 text-left border transition-all",
                category === "전체"
                  ? "border-[#3182F6] bg-[#EBF3FF]"
                  : "border-border bg-white hover:border-[#D1D5DB]",
              ].join(" ")}
            >
              <p className="text-sm font-bold text-[#191F28]">전체</p>
              <p className="text-xs text-[#9CA3AF] mt-0.5">{GLOSSARY.length}개 용어</p>
            </button>
            {CATEGORIES.map((c) => {
              const meta = CATEGORY_META[c];
              const Icon = meta.icon;
              const active = category === c;
              return (
                <button
                  key={c}
                  onClick={() => setCategory(c)}
                  className={[
                    "rounded-2xl p-3.5 text-left border transition-all",
                    active ? "border-[#3182F6]" : "border-border bg-white hover:border-[#D1D5DB]",
                  ].join(" ")}
                  style={active ? { background: meta.bg } : undefined}
                >
                  <Icon size={16} style={{ color: meta.color }} className="mb-1.5" />
                  <p className="text-sm font-bold text-[#191F28]">{c}</p>
                  <p className="text-xs text-[#9CA3AF] mt-0.5">{countByCategory(c)}개 용어</p>
                </button>
              );
            })}
          </div>

          {/* 용어 카드 그리드 */}
          {filtered.length === 0 ? (
            <p className="text-sm text-[#9CA3AF] text-center py-10">검색 결과가 없습니다.</p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {filtered.map((g) => (
                <TermCard key={g.term} term={g} />
              ))}
            </div>
          )}

          <p className="text-xs text-center text-[#9CA3AF] pt-2 pb-4">
            본 용어 설명은 일반적인 개념·사실 안내이며, 특정 종목이나 투자 전략을
            추천하지 않습니다.
          </p>
        </div>
      </main>
    </div>
  );
}
