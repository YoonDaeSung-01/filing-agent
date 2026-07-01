"use client";

import type { StockPrice } from "@/lib/types";

function fmt(v: number) {
  return v.toLocaleString("ko-KR");
}

interface Props {
  data: StockPrice;
  isFetching: boolean;
}

export function StockLivePrice({ data, isFetching }: Props) {
  const up = data.change >= 0;
  const color = up ? "#F04452" : "#1677FF"; // 토스: 상승=빨강, 하락=파랑

  return (
    <div className="bg-white rounded-2xl p-5 shadow-card border border-border">
      <div className="flex items-center justify-between mb-4">
        <div>
          <p className="text-lg font-bold text-[#191F28]">{data.company}</p>
          <p className="text-xs text-[#9CA3AF] mt-0.5 flex items-center gap-1.5">
            {data.ticker} · 한투 KIS
            <span className="inline-flex items-center gap-1">
              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  isFetching ? "bg-[#3182F6] animate-pulse" : "bg-[#22C55E]"
                }`}
              />
              실시간
            </span>
          </p>
        </div>
        <span className="text-xs text-[#6B7280] bg-[#F2F4F6] px-2.5 py-1 rounded-full">
          ⓘ 사실 데이터 · 투자 권유 아님
        </span>
      </div>

      <div className="mb-2">
        <span className="text-4xl font-bold text-[#191F28] tracking-tight">{fmt(data.price)}</span>
        <span className="text-base text-[#6B7280] ml-1">원</span>
      </div>

      <div className="flex items-center gap-2 mb-5">
        <span className="text-sm font-semibold" style={{ color }}>
          {up ? "▲" : "▼"} {fmt(Math.abs(data.change))}원
        </span>
        <span
          className="text-xs px-2 py-0.5 rounded-full font-semibold"
          style={{ color, background: up ? "#FFF0F0" : "#EBF3FF" }}
        >
          {up ? "+" : ""}
          {data.change_pct}%
        </span>
        <span className="text-xs text-[#9CA3AF]">전일 대비</span>
      </div>

      <div className="grid grid-cols-3 gap-3">
        <div className="bg-[#F9FAFB] rounded-xl p-3">
          <p className="text-xs text-[#9CA3AF] mb-1">고가</p>
          <p className="text-sm font-semibold text-[#191F28]">{fmt(data.high)}</p>
        </div>
        <div className="bg-[#F9FAFB] rounded-xl p-3">
          <p className="text-xs text-[#9CA3AF] mb-1">저가</p>
          <p className="text-sm font-semibold text-[#191F28]">{fmt(data.low)}</p>
        </div>
        <div className="bg-[#F9FAFB] rounded-xl p-3">
          <p className="text-xs text-[#9CA3AF] mb-1">거래량</p>
          <p className="text-sm font-semibold text-[#191F28]">{fmt(data.volume)}</p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 mt-3">
        <div className="bg-[#F9FAFB] rounded-xl p-3">
          <p className="text-xs text-[#9CA3AF] mb-1">52주 최고</p>
          <p className="text-sm font-semibold text-[#191F28]">{fmt(data.w52_high)}원</p>
        </div>
        <div className="bg-[#F9FAFB] rounded-xl p-3">
          <p className="text-xs text-[#9CA3AF] mb-1">52주 최저</p>
          <p className="text-sm font-semibold text-[#191F28]">{fmt(data.w52_low)}원</p>
        </div>
      </div>
    </div>
  );
}
