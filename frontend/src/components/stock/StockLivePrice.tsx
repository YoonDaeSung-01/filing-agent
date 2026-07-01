"use client";

import { RefreshCw, Star } from "lucide-react";
import type { StockPrice } from "@/lib/types";
import { useWatchlist } from "@/hooks/useWatchlist";
import { GlossaryTooltip } from "@/components/learn/GlossaryTooltip";

function fmt(v: number) {
  return v.toLocaleString("ko-KR");
}

function clock(ts?: number) {
  if (!ts) return "";
  const d = new Date(ts);
  return d.toLocaleTimeString("ko-KR", { hour12: false });
}

interface Props {
  data: StockPrice;
  isFetching: boolean;
  updatedAt?: number;
  onRefresh?: () => void;
}

export function StockLivePrice({ data, isFetching, updatedAt, onRefresh }: Props) {
  const up = data.change >= 0;
  const color = up ? "#F04452" : "#1677FF"; // 토스: 상승=빨강, 하락=파랑
  const { isWatched, toggle } = useWatchlist();
  const watched = isWatched(data.company);

  return (
    <div className="bg-white rounded-2xl p-5 shadow-card border border-border">
      <div className="flex items-start justify-between mb-4">
        <div>
          <div className="flex items-center gap-1.5">
            <p className="text-lg font-bold text-[#191F28]">{data.company}</p>
            <button
              onClick={() => toggle(data.company)}
              aria-label={watched ? "관심종목에서 제거" : "관심종목에 추가"}
              className="p-0.5 rounded-full hover:bg-[#F2F4F6] transition-colors"
            >
              <Star
                size={16}
                className={watched ? "fill-[#FFB800] text-[#FFB800]" : "text-[#D1D5DB]"}
              />
            </button>
          </div>
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
        <div className="flex flex-col items-end gap-1.5">
          <span className="text-xs text-[#6B7280] bg-[#F2F4F6] px-2.5 py-1 rounded-full">
            ⓘ 사실 데이터 · 투자 권유 아님
          </span>
          <button
            onClick={onRefresh}
            className="flex items-center gap-1 text-[11px] text-[#9CA3AF] hover:text-[#3182F6] transition-colors"
          >
            <RefreshCw size={11} className={isFetching ? "animate-spin" : ""} />
            {updatedAt ? `${clock(updatedAt)} 갱신` : "새로고침"}
          </button>
        </div>
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
          <p className="text-xs text-[#9CA3AF] mb-1 flex items-center gap-1">
            거래량 <GlossaryTooltip term="거래량" />
          </p>
          <p className="text-sm font-semibold text-[#191F28]">{fmt(data.volume)}</p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 mt-3">
        <div className="bg-[#F9FAFB] rounded-xl p-3">
          <p className="text-xs text-[#9CA3AF] mb-1 flex items-center gap-1">
            52주 최고 <GlossaryTooltip term="52주 최고·최저" />
          </p>
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
