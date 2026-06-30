"use client";

import { useState } from "react";
import { formatKRW, formatKRWFull, fsDivLabel } from "@/lib/format";
import type { LookupFact } from "@/lib/types";

export function FinancialCard({ fact }: { fact: LookupFact }) {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    await navigator.clipboard.writeText(String(fact.value));
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="bg-white rounded-2xl p-5 shadow-card border border-border">
      <div className="flex items-start justify-between mb-3">
        <div>
          <p className="text-xs font-semibold text-[#6B7280] uppercase tracking-wider">
            {fact.account}
          </p>
          <p className="text-xs text-[#6B7280] mt-0.5">{fact.year}년</p>
        </div>
        <button
          onClick={copy}
          className="text-xs text-[#6B7280] hover:text-[#3182F6] transition-colors px-2 py-1 rounded-lg hover:bg-[#EBF3FF]"
        >
          {copied ? "✓ 복사됨" : "복사"}
        </button>
      </div>

      <div className="flex items-baseline gap-2 mb-1">
        <span className="text-3xl font-bold text-[#191F28] tracking-tight">
          {formatKRW(fact.value)}
        </span>
        <span className="text-sm text-[#6B7280] font-medium">원</span>
      </div>

      <p className="text-xs text-[#6B7280] mb-3">
        {formatKRWFull(fact.value)}원
      </p>

      <div className="flex items-center gap-2">
        <span className="text-xs bg-[#EBF3FF] text-[#3182F6] px-2 py-0.5 rounded-full font-medium">
          {fsDivLabel(fact.fs_div)}
        </span>
        <span className="text-xs text-[#6B7280]">OpenDART</span>
      </div>
    </div>
  );
}
