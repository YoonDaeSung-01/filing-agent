"use client";

import type { StockSummary } from "@/lib/types";

function fmt(v: number) {
  return v.toLocaleString("ko-KR");
}

interface Props {
  data: StockSummary;
}

export function StockSummaryCard({ data }: Props) {
  const isUp = data.change >= 0;
  const changeColor = isUp ? "#F04452" : "#1677FF"; // 토스: 상승=빨강, 하락=파랑

  return (
    <div className="bg-white rounded-2xl p-5 shadow-card border border-border">
      {/* 종목 헤더 */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <p className="text-lg font-bold text-[#191F28]">{data.company}</p>
          <p className="text-xs text-[#9CA3AF] mt-0.5">{data.ticker} · KRX · {data.date}</p>
        </div>
        <span className="text-xs text-[#6B7280] bg-[#F2F4F6] px-2.5 py-1 rounded-full">
          ⓘ 사실 데이터 · 투자 권유 아님
        </span>
      </div>

      {/* 현재가 */}
      <div className="mb-4">
        <span className="text-4xl font-bold text-[#191F28] tracking-tight">
          {fmt(data.close)}
        </span>
        <span className="text-base text-[#6B7280] ml-1">원</span>
      </div>

      {/* 등락 */}
      <div className="flex items-center gap-2 mb-5">
        <span className="text-sm font-semibold" style={{ color: changeColor }}>
          {isUp ? "▲" : "▼"} {fmt(Math.abs(data.change))}원
        </span>
        {data.change_pct !== null && (
          <span className="text-xs px-2 py-0.5 rounded-full font-semibold"
            style={{ color: changeColor, background: isUp ? "#FFF0F0" : "#EBF3FF" }}>
            {isUp ? "+" : ""}{data.change_pct}%
          </span>
        )}
        <span className="text-xs text-[#9CA3AF]">전일 대비</span>
      </div>

      {/* 52주 범위 */}
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-[#F9FAFB] rounded-xl p-3">
          <p className="text-xs text-[#9CA3AF] mb-1">52주 최고</p>
          <p className="text-sm font-semibold text-[#191F28]">{fmt(data.high_52w)}원</p>
        </div>
        <div className="bg-[#F9FAFB] rounded-xl p-3">
          <p className="text-xs text-[#9CA3AF] mb-1">52주 최저</p>
          <p className="text-sm font-semibold text-[#191F28]">{fmt(data.low_52w)}원</p>
        </div>
      </div>
    </div>
  );
}
