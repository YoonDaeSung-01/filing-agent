"use client";

import { useState } from "react";
import { useAsk } from "@/hooks/useAsk";
import { AnswerCard, AnswerSkeleton } from "@/components/result/AnswerCard";

function presets(company: string) {
  return [
    { label: "위험 요인", q: `${company}가 최근 사업보고서에서 밝힌 주요 위험 요인은?` },
    { label: "사업 전략", q: `${company} 사업보고서의 주요 사업 전략을 설명해줘` },
    { label: "매출액", q: `${company} 2024년 매출액은?` },
    { label: "영업이익 증감", q: `${company}의 2023년 대비 2024년 영업이익 증감은?` },
  ];
}

export function StockAIPanel({ company }: { company: string }) {
  const { mutate, data, isPending, error } = useAsk();
  const [input, setInput] = useState("");

  const submit = (q: string) => {
    if (!q.trim() || isPending) return;
    mutate({ question: q, company });
  };

  return (
    <div className="bg-white rounded-2xl p-5 shadow-card border border-border">
      <div className="flex items-center gap-2 mb-0.5">
        <span className="text-base">🤖</span>
        <p className="text-sm font-bold text-[#191F28]">AI 공시 분석</p>
      </div>
      <p className="text-xs text-[#9CA3AF] mb-4">
        {company}의 공시·재무를 근거와 함께 (투자 조언 아님)
      </p>

      {/* 프리셋 질문 */}
      <div className="flex flex-wrap gap-1.5 mb-3">
        {presets(company).map((p) => (
          <button
            key={p.label}
            onClick={() => submit(p.q)}
            disabled={isPending}
            className="text-xs px-2.5 py-1.5 rounded-full bg-[#EBF3FF] text-[#3182F6] font-medium hover:bg-[#DBEAFE] disabled:opacity-50 transition-colors"
          >
            {p.label}
          </button>
        ))}
      </div>

      {/* 자유 입력 */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit(input);
        }}
        className="flex gap-2 mb-4"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="공시에 대해 물어보세요"
          className="flex-1 min-w-0 text-sm border border-border rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-[#3182F6]"
        />
        <button
          type="submit"
          disabled={isPending || !input.trim()}
          className="text-sm font-semibold bg-[#3182F6] text-white px-3 py-2 rounded-xl disabled:opacity-50 shrink-0"
        >
          질문
        </button>
      </form>

      {/* 결과 */}
      {isPending && <AnswerSkeleton />}
      {error && !isPending && (
        <p className="text-xs text-[#92400E]">오류: {error.message}</p>
      )}
      {data && !isPending && data.status === "blocked" && (
        <div className="rounded-xl bg-[#FFFBEB] border border-[#FDE68A] p-4 text-sm text-[#92400E]">
          {data.answer}
        </div>
      )}
      {data && !isPending && data.status !== "blocked" && (
        <AnswerCard
          answer={data.answer}
          sources={data.sources}
          variant={data.status === "failed" ? "warning" : "normal"}
        />
      )}
    </div>
  );
}
