"use client";

import { useState } from "react";
import { Header } from "@/components/layout/Header";
import { StockChart } from "@/components/stock/StockChart";
import { StockSummaryCard } from "@/components/stock/StockSummary";
import { useStock } from "@/hooks/useStock";
import { TARGET_COMPANIES } from "@/lib/constants";

const PERIOD_OPTIONS = [
  { label: "1개월", days: 30 },
  { label: "3개월", days: 90 },
  { label: "6개월", days: 180 },
  { label: "1년", days: 365 },
  { label: "3년", days: 1095 },
];

export default function StocksPage() {
  const [company, setCompany] = useState<string>(TARGET_COMPANIES[0]);
  const [period, setPeriod] = useState(365);

  const { data, isLoading, error } = useStock(company, period);

  return (
    <div className="flex flex-col h-screen">
      <Header />

      <main className="flex-1 overflow-y-auto p-4 md:p-6 bg-[#F9FAFB]">
        <div className="max-w-3xl mx-auto space-y-4">

          {/* 컨트롤 바 */}
          <div className="flex flex-wrap gap-3 items-center">
            {/* 종목 선택 */}
            <select
              value={company}
              onChange={(e) => setCompany(e.target.value)}
              className="flex-1 min-w-[140px] text-sm font-medium bg-white border border-border rounded-xl px-3 py-2.5 text-[#191F28] focus:outline-none focus:ring-2 focus:ring-[#3182F6]"
            >
              {TARGET_COMPANIES.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>

            {/* 기간 선택 */}
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

          {/* 로딩 */}
          {isLoading && (
            <div className="bg-white rounded-2xl p-5 shadow-card border border-border animate-pulse">
              <div className="h-6 w-32 bg-[#F2F4F6] rounded mb-3" />
              <div className="h-10 w-48 bg-[#F2F4F6] rounded mb-4" />
              <div className="h-[240px] bg-[#F2F4F6] rounded-xl" />
            </div>
          )}

          {/* 에러 */}
          {error && !isLoading && (
            <div className="bg-[#FFF7ED] border border-[#FED7AA] rounded-2xl p-5">
              <div className="flex items-center gap-2 mb-1">
                <span>⚠️</span>
                <span className="text-sm font-semibold text-[#92400E]">
                  주가 데이터를 불러올 수 없습니다
                </span>
              </div>
              <p className="text-xs text-[#92400E]">{error.message}</p>
            </div>
          )}

          {/* 데이터 */}
          {data && !isLoading && (
            <>
              {!data.found ? (
                <div className="bg-[#FFF7ED] border border-[#FED7AA] rounded-2xl p-5">
                  <p className="text-sm font-semibold text-[#92400E]">⚠️ {data.reason}</p>
                </div>
              ) : (
                <>
                  <StockSummaryCard data={data} />

                  <div className="bg-white rounded-2xl p-5 shadow-card border border-border">
                    <p className="text-xs font-semibold text-[#6B7280] uppercase tracking-wider mb-4">
                      주가 추이
                    </p>
                    <StockChart data={data.ohlc} period={period} />
                  </div>

                  <p className="text-xs text-center text-[#9CA3AF]">
                    본 정보는 KRX 공개 데이터 기반 사실 정보이며 투자 권유·투자 조언이 아닙니다.
                    투자 판단의 책임은 투자자 본인에게 있습니다.
                  </p>
                </>
              )}
            </>
          )}

        </div>
      </main>
    </div>
  );
}
