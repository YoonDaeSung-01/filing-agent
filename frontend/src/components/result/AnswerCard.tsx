"use client";

import { motion } from "framer-motion";
import { Skeleton } from "@/components/ui/skeleton";

interface AnswerCardProps {
  answer: string;
  sources: string[];
  variant?: "normal" | "warning";
}

export function AnswerCard({ answer, sources, variant = "normal" }: AnswerCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className={`rounded-2xl p-5 border ${
        variant === "warning"
          ? "bg-[#FFFBEB] border-[#FDE68A]"
          : "bg-white border-border shadow-card"
      }`}
    >
      {variant === "warning" && (
        <div className="flex items-center gap-1.5 mb-3">
          <span className="text-sm">⚠️</span>
          <span className="text-xs font-semibold text-[#92400E]">
            부분 확인 — 질문을 회사·연도·계정으로 좁혀 재시도해 주세요
          </span>
        </div>
      )}
      <p className="text-sm text-[#191F28] leading-relaxed whitespace-pre-wrap">
        {answer}
      </p>
      {sources.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-3 pt-3 border-t border-border">
          {sources.map((src, i) => (
            <span
              key={i}
              className="text-xs bg-[#F2F4F6] text-[#6B7280] px-2.5 py-1 rounded-full"
            >
              {src}
            </span>
          ))}
        </div>
      )}
    </motion.div>
  );
}

export function AnswerSkeleton() {
  return (
    <div className="bg-white rounded-2xl p-5 border border-border shadow-card space-y-3">
      <Skeleton className="h-4 w-3/4 bg-[#F2F4F6]" />
      <Skeleton className="h-4 w-full bg-[#F2F4F6]" />
      <Skeleton className="h-4 w-5/6 bg-[#F2F4F6]" />
    </div>
  );
}
