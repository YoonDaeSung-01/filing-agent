"use client";

import Link from "next/link";
import { TrendingUp, TrendingDown } from "lucide-react";
import { useBalance } from "@/hooks/usePaper";
import { useMarketMovers, useMarketSectors } from "@/hooks/useMarket";
import { GlossaryTooltip } from "@/components/learn/GlossaryTooltip";
import type { MarketMover, SectorStock } from "@/lib/types";

function fmt(v: number) {
  return v.toLocaleString("ko-KR");
}

function MoverRow({ item }: { item: MarketMover }) {
  const up = item.change >= 0;
  const color = up ? "#F04452" : "#1677FF";
  return (
    <Link
      href={`/stocks?company=${encodeURIComponent(item.name)}`}
      className="flex items-center justify-between px-3 py-2.5 rounded-xl hover:bg-[#F9FAFB] transition-colors"
    >
      <span className="text-sm text-[#191F28] truncate">{item.name}</span>
      <div className="text-right shrink-0 ml-2">
        <span className="text-sm font-semibold text-[#191F28]">{fmt(item.price)}</span>
        <span className="text-xs font-medium ml-1.5" style={{ color }}>
          {up ? "+" : ""}
          {item.change_pct}%
        </span>
      </div>
    </Link>
  );
}

function SectorCard({ sector }: { sector: { sector: string; stocks: SectorStock[] } }) {
  return (
    <div className="bg-white rounded-2xl p-4 border border-border shadow-card">
      <p className="text-xs font-semibold text-[#6B7280] uppercase tracking-wider mb-2.5">
        {sector.sector}
      </p>
      <div className="space-y-1">
        {sector.stocks.map((s) => {
          const up = s.change >= 0;
          const color = up ? "#F04452" : "#1677FF";
          return (
            <Link
              key={s.ticker}
              href={`/stocks?company=${encodeURIComponent(s.company)}`}
              className="flex items-center justify-between px-2 py-1.5 rounded-lg hover:bg-[#F9FAFB] transition-colors"
            >
              <span className="text-sm text-[#191F28]">{s.company}</span>
              <div className="text-right">
                <span className="text-sm font-medium text-[#191F28]">{fmt(s.price)}</span>
                <span className="text-xs font-medium ml-1.5" style={{ color }}>
                  {up ? "+" : ""}
                  {s.change_pct}%
                </span>
              </div>
            </Link>
          );
        })}
        {sector.stocks.length === 0 && (
          <p className="text-xs text-[#D1D5DB] px-2 py-1.5">시세를 불러올 수 없습니다</p>
        )}
      </div>
    </div>
  );
}

export function MarketDashboard() {
  const balance = useBalance();
  const movers = useMarketMovers();
  const sectors = useMarketSectors();

  return (
    <div className="max-w-5xl mx-auto space-y-4">
      {/* 내 모의투자 요약 */}
      {balance.data && balance.data.found && (
        <div className="bg-white rounded-2xl border border-border shadow-card p-5">
          <p className="text-sm font-bold text-[#191F28] mb-3">내 모의투자</p>
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-[#F9FAFB] rounded-xl p-3">
              <p className="text-xs text-[#9CA3AF] mb-1 flex items-center gap-1">
                예수금 <GlossaryTooltip term="예수금" />
              </p>
              <p className="text-sm font-bold text-[#191F28]">{fmt(balance.data.cash)}원</p>
            </div>
            <div className="bg-[#F9FAFB] rounded-xl p-3">
              <p className="text-xs text-[#9CA3AF] mb-1 flex items-center gap-1">
                총 평가금액 <GlossaryTooltip term="평가금액" />
              </p>
              <p className="text-sm font-bold text-[#191F28]">{fmt(balance.data.eval_amount)}원</p>
            </div>
            <div className="bg-[#F9FAFB] rounded-xl p-3">
              <p className="text-xs text-[#9CA3AF] mb-1 flex items-center gap-1">
                평가손익 <GlossaryTooltip term="평가손익" />
              </p>
              <p
                className="text-sm font-bold"
                style={{ color: balance.data.pnl >= 0 ? "#F04452" : "#1677FF" }}
              >
                {balance.data.pnl >= 0 ? "+" : ""}
                {fmt(balance.data.pnl)}원 ({balance.data.pnl >= 0 ? "+" : ""}
                {balance.data.pnl_rate}%)
              </p>
            </div>
          </div>
        </div>
      )}

      {/* 시장 전체 상승/하락 순위 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-white rounded-2xl border border-border shadow-card p-4">
          <div className="flex items-center gap-1.5 mb-2 px-1">
            <TrendingUp size={14} className="text-[#F04452]" />
            <p className="text-xs font-semibold text-[#6B7280] uppercase tracking-wider">
              상승률 상위 (시장 전체)
            </p>
          </div>
          {movers.isLoading && (
            <div className="h-40 bg-[#F2F4F6] rounded-xl animate-pulse mx-1" />
          )}
          {movers.data && movers.data.found && (
            <div>
              {movers.data.gainers.slice(0, 8).map((m) => (
                <MoverRow key={m.ticker} item={m} />
              ))}
            </div>
          )}
          {movers.data && !movers.data.found && (
            <p className="text-xs text-[#92400E] px-2">{movers.data.reason}</p>
          )}
        </div>

        <div className="bg-white rounded-2xl border border-border shadow-card p-4">
          <div className="flex items-center gap-1.5 mb-2 px-1">
            <TrendingDown size={14} className="text-[#1677FF]" />
            <p className="text-xs font-semibold text-[#6B7280] uppercase tracking-wider">
              하락률 상위 (시장 전체)
            </p>
          </div>
          {movers.isLoading && (
            <div className="h-40 bg-[#F2F4F6] rounded-xl animate-pulse mx-1" />
          )}
          {movers.data && movers.data.found && (
            <div>
              {movers.data.losers.slice(0, 8).map((m) => (
                <MoverRow key={m.ticker} item={m} />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* 관심 분야 시세 */}
      <div>
        <p className="text-xs font-semibold text-[#6B7280] uppercase tracking-wider mb-2 px-1">
          분야별 시세 (관심 종목)
        </p>
        {sectors.isLoading && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {[0, 1, 2, 3].map((i) => (
              <div key={i} className="h-32 bg-[#F2F4F6] rounded-2xl animate-pulse" />
            ))}
          </div>
        )}
        {sectors.data && sectors.data.found && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {sectors.data.sectors.map((s) => (
              <SectorCard key={s.sector} sector={s} />
            ))}
          </div>
        )}
        {sectors.data && !sectors.data.found && (
          <p className="text-xs text-[#92400E]">{sectors.data.reason}</p>
        )}
      </div>

      <p className="text-xs text-center text-[#9CA3AF] pt-1">
        순위·시세는 사실 데이터이며 투자 권유·추천이 아닙니다. &ldquo;분야별 시세&rdquo;는 전체
        시장 업종 분류가 아닌 관심 종목 10개 한정 분류입니다.
      </p>
    </div>
  );
}
