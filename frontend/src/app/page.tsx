"use client";

import { useState } from "react";
import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";
import { QueryForm } from "@/components/query/QueryForm";
import { ResultPanel } from "@/components/result/ResultPanel";
import { useAsk } from "@/hooks/useAsk";
import { useQueryHistory } from "@/hooks/useQueryHistory";
import type { HistoryItem } from "@/hooks/useQueryHistory";

export default function Home() {
  const { mutate, data, isPending, reset, error } = useAsk();
  const { history, addToHistory, clearHistory } = useQueryHistory();

  const [formState, setFormState] = useState({
    question: "",
    company: "삼성전자",
    year: 2025,
  });

  const handleSubmit = (question: string, company: string, year: number) => {
    const req = { question, company: company || null, year };
    addToHistory({ question, company, year });
    mutate(req);
    setFormState({ question, company, year });
  };

  const handleHistorySelect = (item: HistoryItem) => {
    setFormState({
      question: item.question,
      company: item.company ?? "삼성전자",
      year: item.year ?? 2025,
    });
    reset();
  };

  const handleExampleClick = (q: string) => {
    setFormState((prev) => ({ ...prev, question: q }));
  };

  return (
    <div className="flex flex-col h-screen">
      <Header />
      <div className="flex flex-1 overflow-hidden">
        {/* 사이드바 — 데스크톱만 */}
        <div className="hidden md:block">
          <Sidebar
            history={history}
            onSelect={handleHistorySelect}
            onClear={clearHistory}
          />
        </div>

        {/* 메인 영역 */}
        <main className="flex-1 overflow-y-auto p-4 md:p-6">
          <div className="max-w-2xl mx-auto space-y-6">
            <QueryForm
              onSubmit={handleSubmit}
              isPending={isPending}
              initialQuestion={formState.question}
              initialCompany={formState.company}
              initialYear={formState.year}
            />

            <div className="border-t border-border" />

            <ResultPanel
              response={data ?? null}
              isPending={isPending}
              error={error}
              onExampleClick={handleExampleClick}
            />
          </div>
        </main>
      </div>
    </div>
  );
}
