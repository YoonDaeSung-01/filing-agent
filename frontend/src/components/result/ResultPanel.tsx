"use client";

import { motion, AnimatePresence } from "framer-motion";
import type { AskResponse } from "@/lib/types";
import { ToolTimeline } from "./ToolTimeline";
import { FactCards } from "./FactCards";
import { AnswerCard, AnswerSkeleton } from "./AnswerCard";
import { GuardrailNotice } from "./GuardrailNotice";
import { SourcePanel } from "./SourcePanel";

const EXAMPLE_QUESTIONS = [
  { icon: "📊", text: "삼성전자 2024년 매출액은?" },
  { icon: "📈", text: "SK하이닉스 2023 대비 2024년 영업이익 증감은?" },
  { icon: "📄", text: "현대자동차 2024년 사업보고서 주요 위험 요인은?" },
];

interface ResultPanelProps {
  response: AskResponse | null;
  isPending: boolean;
  error: Error | null;
  onExampleClick: (q: string) => void;
}

export function ResultPanel({ response, isPending, error, onExampleClick }: ResultPanelProps) {
  // 로딩 중
  if (isPending) {
    return (
      <div className="space-y-4">
        <div className="space-y-1.5">
          <p className="text-xs font-semibold text-[#6B7280] uppercase tracking-wider">
            도구 실행
          </p>
          <div className="flex items-center gap-2 px-3 py-2 bg-[#F2F4F6] rounded-xl animate-pulse">
            <span className="text-sm">⏳</span>
            <span className="text-sm text-[#6B7280]">에이전트가 도구를 선택하는 중...</span>
          </div>
        </div>
        <AnswerSkeleton />
      </div>
    );
  }

  // API 오류 (백엔드 미실행, 네트워크 오류 등)
  if (error) {
    const isNetwork = error.message.includes("fetch") || error.message.includes("연결") || error.message.includes("Failed");
    return (
      <div className="bg-[#FFF7ED] border border-[#FED7AA] rounded-2xl p-5">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-base">⚠️</span>
          <span className="text-sm font-semibold text-[#92400E]">
            {isNetwork ? "백엔드 서버에 연결할 수 없습니다" : "요청 처리 중 오류가 발생했습니다"}
          </span>
        </div>
        {isNetwork && (
          <p className="text-xs text-[#92400E] leading-relaxed">
            FastAPI 서버를 먼저 실행해 주세요:<br />
            <code className="bg-[#FEF3C7] px-1.5 py-0.5 rounded font-mono mt-1 inline-block">
              uv run uvicorn filing_agent.api.main:app --reload
            </code>
          </p>
        )}
        {!isNetwork && (
          <p className="text-xs text-[#92400E]">{error.message}</p>
        )}
      </div>
    );
  }

  // 빈 상태 — 온보딩
  if (!response) {
    return (
      <div className="space-y-3">
        <p className="text-xs font-semibold text-[#6B7280] uppercase tracking-wider">
          이런 질문을 해보세요
        </p>
        <div className="grid gap-2">
          {EXAMPLE_QUESTIONS.map((ex) => (
            <button
              key={ex.text}
              onClick={() => onExampleClick(ex.text)}
              className="flex items-center gap-3 text-left px-4 py-3 bg-white rounded-2xl border border-border shadow-card hover:border-[#3182F6] hover:shadow-card-hover transition-all group"
            >
              <span className="text-xl">{ex.icon}</span>
              <span className="text-sm text-[#6B7280] group-hover:text-[#3182F6] transition-colors">
                {ex.text}
              </span>
            </button>
          ))}
        </div>
      </div>
    );
  }

  // 가드레일 차단
  if (response.status === "blocked") {
    return <GuardrailNotice message={response.answer} />;
  }

  // 우아한 실패
  if (response.status === "failed") {
    return (
      <AnswerCard
        answer={response.answer}
        sources={response.sources}
        variant="warning"
      />
    );
  }

  // 정상 응답
  return (
    <AnimatePresence mode="wait">
      <motion.div
        key="result"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="space-y-4"
      >
        <ToolTimeline toolLog={response.tool_log} />
        <FactCards facts={response.facts} />
        <AnswerCard answer={response.answer} sources={[]} />
        <SourcePanel sources={response.sources} />
      </motion.div>
    </AnimatePresence>
  );
}
