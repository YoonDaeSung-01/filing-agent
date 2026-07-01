"use client";

import { useState, useEffect } from "react";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { CompanySelector } from "./CompanySelector";
import { YearSelector } from "./YearSelector";
import { QuickQueries } from "./QuickQueries";

interface QueryFormProps {
  onSubmit: (question: string, company: string, year: number) => void;
  isPending: boolean;
  initialQuestion?: string;
  initialCompany?: string;
  initialYear?: number;
}

export function QueryForm({
  onSubmit,
  isPending,
  initialQuestion = "",
  initialCompany = "삼성전자",
  initialYear = 2025,
}: QueryFormProps) {
  const [question, setQuestion] = useState(initialQuestion);
  const [company, setCompany] = useState(initialCompany);
  const [year, setYear] = useState(initialYear);

  // 히스토리에서 재실행 시 외부 값 반영
  useEffect(() => { setQuestion(initialQuestion); }, [initialQuestion]);
  useEffect(() => { setCompany(initialCompany); }, [initialCompany]);
  useEffect(() => { if (initialYear) setYear(initialYear); }, [initialYear]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim() || isPending) return;
    onSubmit(question.trim(), company, year);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as unknown as React.FormEvent);
    }
  };

  return (
    <div className="space-y-4">
      <QuickQueries
        company={company}
        year={year}
        onSelect={(q) => setQuestion(q)}
      />

      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="flex gap-3">
          <div className="flex-1">
            <CompanySelector value={company} onChange={setCompany} />
          </div>
          <div className="w-52">
            <YearSelector value={year} onChange={setYear} />
          </div>
        </div>

        <div className="relative">
          <Textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="질문을 입력하세요 (Enter로 제출, Shift+Enter로 줄바꿈)"
            className="min-h-[80px] resize-none rounded-xl border-border text-sm text-[#191F28] placeholder:text-[#6B7280] focus:ring-2 focus:ring-[#3182F6] pr-24"
            disabled={isPending}
          />
          <Button
            type="submit"
            disabled={!question.trim() || isPending}
            className="absolute bottom-3 right-3 bg-[#3182F6] hover:bg-[#1C6FE0] text-white text-sm px-4 py-1.5 h-auto rounded-lg font-medium transition-colors disabled:opacity-50"
          >
            {isPending ? "조회 중..." : "질의하기 →"}
          </Button>
        </div>
      </form>
    </div>
  );
}
