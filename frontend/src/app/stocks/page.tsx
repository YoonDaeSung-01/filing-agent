"use client";

import { useState } from "react";
import { Header } from "@/components/layout/Header";
import { StockChart } from "@/components/stock/StockChart";
import { StockLivePrice } from "@/components/stock/StockLivePrice";
import { StockAIPanel } from "@/components/stock/StockAIPanel";
import { OrderPanel } from "@/components/stock/OrderPanel";
import { PortfolioCard } from "@/components/stock/PortfolioCard";
import { JournalCard } from "@/components/stock/JournalCard";
import { NewsPanel } from "@/components/stock/NewsPanel";
import { SearchBox } from "@/components/stock/SearchBox";
import { WatchlistBar } from "@/components/stock/WatchlistBar";
import { useStock, useStockPrice, useIntraday } from "@/hooks/useStock";
import { useBalance } from "@/hooks/usePaper";
import { TARGET_COMPANIES } from "@/lib/constants";

function fmt(v: number) {
  return v.toLocaleString("ko-KR");
}

const PERIOD_OPTIONS = [
  { label: "실시간", days: 0 }, // 당일 분봉
  { label: "1주", days: 7 },
  { label: "1개월", days: 30 },
  { label: "3개월", days: 90 },
  { label: "1년", days: 365 },
  { label: "3년", days: 1095 },
];

export default function StocksPage() {
  const [company, setCompany] = useState<string>(TARGET_COMPANIES[0]);
  const [period, setPeriod] = useState(365);

  // 실시간(당일 분봉)은 한투, 그 외 기간은 FDR 일봉
  const isIntraday = period === 0;
  const price = useStockPrice(company);
  const chart = useStock(company, period, !isIntraday);
  const intraday = useIntraday(company, isIntraday);
  const balance = useBalance();

  // 차트 데이터 소스 선택
  const cLoading = isIntraday ? intraday.isLoading : chart.isLoading;
  const cError = isIntraday ? intraday.error : chart.error;
  const cData = isIntraday ? intraday.data : chart.data;

  // 현재 종목 보유 수량(매도 활성 조건) — 종목코드 우선, 로딩 중엔 회사명으로 폴백
  // (종목 전환 직후 현재가 쿼리가 아직 안 끝났을 때 매도 탭이 잠깐 깜빡이는 것 방지)
  const currentTicker = price.data?.found ? price.data.ticker : undefined;
  const positions = balance.data?.found ? balance.data.positions : [];
  const heldQty = currentTicker
    ? (positions.find((p) => p.ticker === currentTicker)?.qty ?? 0)
    : (positions.find((p) => p.name === company)?.qty ?? 0);

  return (
    <div className="flex flex-col h-screen">
      <Header />

      <main className="flex-1 overflow-y-auto p-4 md:p-6 bg-[#F9FAFB]">
        <div className="max-w-6xl mx-auto space-y-4">
          {/* 상단: 잔고 요약 바 */}
          {balance.data && balance.data.found && (
            <div className="flex flex-wrap items-center gap-x-6 gap-y-2 bg-white border border-border rounded-2xl px-5 py-3 shadow-card">
              <div className="flex items-center gap-2">
                <span className="text-xs text-[#9CA3AF]">예수금</span>
                <span className="text-sm font-bold text-[#191F28]">
                  {fmt(balance.data.cash)}원
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-[#9CA3AF]">총 평가</span>
                <span className="text-sm font-bold text-[#191F28]">
                  {fmt(balance.data.eval_amount)}원
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-[#9CA3AF]">평가손익</span>
                <span
                  className="text-sm font-bold"
                  style={{ color: balance.data.pnl >= 0 ? "#F04452" : "#1677FF" }}
                >
                  {balance.data.pnl >= 0 ? "+" : ""}
                  {fmt(balance.data.pnl)} ({balance.data.pnl >= 0 ? "+" : ""}
                  {balance.data.pnl_rate}%)
                </span>
              </div>
              <span className="text-[11px] text-[#9CA3AF] ml-auto">모의투자 · 가상자금</span>
            </div>
          )}

          {/* 컨트롤 바 — 검색 + 기간 */}
          <div className="flex flex-wrap gap-3 items-center">
            <SearchBox company={company} onSelect={setCompany} />

            <div className="flex gap-1.5 bg-white border border-border rounded-xl p-1">
              {PERIOD_OPTIONS.map((opt) => (
                <button
                  key={opt.days}
                  onClick={() => setPeriod(opt.days)}
                  className={[
                    "px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors",
                    period === opt.days
                      ? "bg-[#3182F6] text-white"
                      : "text-[#6B7280] hover:text-[#191F28]",
                  ].join(" ")}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* 관심종목 — 원탭 전환 */}
          <WatchlistBar activeCompany={company} onSelect={setCompany} />

          {/* 2단 레이아웃 — 좌: 시세·차트 / 우: 종목 분석(sticky) */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 items-start">
            {/* 좌측 (2/3) */}
            <div className="lg:col-span-2 space-y-4">
              {/* 실시간 현재가 */}
              {price.isLoading && (
                <div className="bg-white rounded-2xl p-5 shadow-card border border-border animate-pulse">
                  <div className="h-6 w-32 bg-[#F2F4F6] rounded mb-3" />
                  <div className="h-10 w-48 bg-[#F2F4F6] rounded" />
                </div>
              )}
              {price.error && !price.isLoading && (
                <div className="bg-[#FFF7ED] border border-[#FED7AA] rounded-2xl p-5">
                  <p className="text-sm font-semibold text-[#92400E]">
                    ⚠️ 현재가를 불러올 수 없습니다
                  </p>
                  <p className="text-xs text-[#92400E] mt-1">{price.error.message}</p>
                </div>
              )}
              {price.data && !price.isLoading && !price.data.found && (
                <div className="bg-[#FFF7ED] border border-[#FED7AA] rounded-2xl p-5">
                  <p className="text-sm font-semibold text-[#92400E]">⚠️ {price.data.reason}</p>
                </div>
              )}
              {price.data && price.data.found && (
                <StockLivePrice
                  data={price.data}
                  isFetching={price.isFetching}
                  updatedAt={price.dataUpdatedAt}
                  onRefresh={() => price.refetch()}
                />
              )}

              {/* 차트 — 실시간(분봉) 또는 일봉 */}
              <div className="bg-white rounded-2xl p-5 shadow-card border border-border">
                <p className="text-xs font-semibold text-[#6B7280] uppercase tracking-wider mb-4">
                  {isIntraday ? "당일 분봉 (실시간)" : "주가 추이 (일봉)"}
                </p>
                {cLoading && <div className="h-[240px] bg-[#F2F4F6] rounded-xl animate-pulse" />}
                {cError && !cLoading && (
                  <p className="text-xs text-[#92400E]">
                    차트를 불러올 수 없습니다: {cError.message}
                  </p>
                )}
                {cData && cData.found && cData.ohlc.length > 0 && (
                  <StockChart data={cData.ohlc} period={period} intraday={isIntraday} />
                )}
                {cData && cData.found && cData.ohlc.length === 0 && (
                  <p className="text-xs text-[#9CA3AF] text-center py-10">
                    분봉 데이터가 없습니다 (장 시작 전이거나 휴장).
                  </p>
                )}
                {cData && !cData.found && (
                  <p className="text-xs text-[#92400E]">{cData.reason}</p>
                )}
              </div>

              {/* 관련 뉴스 */}
              <NewsPanel key={company} company={company} />

              {/* 내 모의투자 (포트폴리오) */}
              <PortfolioCard />
              <JournalCard />

              <p className="text-xs text-[#9CA3AF]">
                본 정보는 한투 KIS·KRX 공개 데이터 기반 사실 정보이며 투자 권유·투자 조언이
                아닙니다. 투자 판단의 책임은 투자자 본인에게 있습니다.
              </p>
            </div>

            {/* 우측 (1/3) — 주문 + 종목 분석, 스크롤 따라감 */}
            <div className="lg:col-span-1">
              <div className="lg:sticky lg:top-4 space-y-4">
                <OrderPanel
                  company={company}
                  currentPrice={price.data?.found ? price.data.price : undefined}
                  heldQty={heldQty}
                />
                <StockAIPanel key={company} company={company} />
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
