"use client";

import { useState } from "react";
import { Copy, Check } from "lucide-react";
import { formatKRW, formatKRWFull, fsDivLabel } from "@/lib/format";
import { TrendSparkline } from "./TrendSparkline";
import { useFinancialTrend } from "@/hooks/useStock";
import type { LookupFact } from "@/lib/types";

function formatSource(raw: string): string {
  // "OpenDART fnlttSinglAcnt.json (corp_code=..., ...)" → 사람이 읽는 문자열
  if (raw.startsWith("OpenDART")) return "OpenDART 전자공시";
  return raw;
}

interface Props {
  fact: LookupFact;
}

export function FinancialCard({ fact }: Props) {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    await navigator.clipboard.writeText(String(fact.value));
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  // 3개년 추이 lazy fetch
  const { data: trend } = useFinancialTrend(fact.company, fact.account);
  const trendPoints = trend?.found ? trend.points : null;

  // 전년 대비 증감률 계산 (추이 데이터가 있을 때만)
  const yoyBadge = (() => {
    if (!trendPoints || trendPoints.length < 2) return null;
    const cur = trendPoints.find((p) => p.year === fact.year);
    const prev = trendPoints.find((p) => p.year === fact.year - 1);
    if (!cur?.value || !prev?.value) return null;
    const pct = ((cur.value - prev.value) / Math.abs(prev.value)) * 100;
    return { pct: pct.toFixed(1), up: pct >= 0 };
  })();

  return (
    <div className="bg-white rounded-2xl p-5 shadow-card border border-border">
      {/* 헤더 */}
      <div className="flex items-start justify-between mb-2">
        <div>
          <p className="text-xs font-semibold text-[#6B7280] uppercase tracking-wider">
            {fact.account}
          </p>
          <p className="text-xs text-[#9CA3AF] mt-0.5">
            {fact.company} · {fact.year}년
          </p>
        </div>
        <button
          onClick={copy}
          aria-label="값 복사"
          className="p-1.5 rounded-lg text-[#9CA3AF] hover:text-[#3182F6] hover:bg-[#EBF3FF] transition-colors"
        >
          {copied ? <Check size={14} className="text-[#3182F6]" /> : <Copy size={14} />}
        </button>
      </div>

      {/* 금액 */}
      <div className="flex items-baseline gap-2 mb-0.5">
        <span className="text-3xl font-bold text-[#191F28] tracking-tight">
          {formatKRW(fact.value)}
        </span>
        <span className="text-sm text-[#6B7280] font-medium">원</span>
        {yoyBadge && (
          <span
            className="text-xs px-1.5 py-0.5 rounded-full font-semibold"
            style={{
              color: yoyBadge.up ? "#F04452" : "#1677FF",
              background: yoyBadge.up ? "#FFF0F0" : "#EBF3FF",
            }}
          >
            {yoyBadge.up ? "▲" : "▼"} {yoyBadge.up ? "+" : ""}{yoyBadge.pct}% YoY
          </span>
        )}
      </div>
      <p className="text-xs text-[#9CA3AF] mb-3">{formatKRWFull(fact.value)}원</p>

      {/* 추이 스파크라인 */}
      {trendPoints && trendPoints.length >= 2 && (
        <div className="mb-3">
          <TrendSparkline points={trendPoints} />
          <div className="flex justify-between text-[10px] text-[#9CA3AF] mt-1 px-0.5">
            {trendPoints.map((p) => (
              <span key={p.year}>{p.year}</span>
            ))}
          </div>
        </div>
      )}

      {/* 출처 배지 */}
      <div className="flex items-center gap-2">
        <span className="text-xs bg-[#EBF3FF] text-[#3182F6] px-2 py-0.5 rounded-full font-medium">
          {fsDivLabel(fact.fs_div)}
        </span>
        <span className="text-xs text-[#9CA3AF]">{formatSource(fact.source)}</span>
      </div>
    </div>
  );
}
