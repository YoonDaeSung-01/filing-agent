"use client";

import { useBalance } from "@/hooks/usePaper";
import { GlossaryTooltip } from "@/components/learn/GlossaryTooltip";

function fmt(v: number) {
  return v.toLocaleString("ko-KR");
}

export function PortfolioCard() {
  const { data, isLoading, error } = useBalance();

  if (isLoading) {
    return (
      <div className="bg-white rounded-2xl p-5 shadow-card border border-border animate-pulse h-40" />
    );
  }
  if (error) {
    return (
      <div className="bg-[#FFF7ED] border border-[#FED7AA] rounded-2xl p-5">
        <p className="text-sm font-semibold text-[#92400E]">⚠️ 모의투자 잔고를 불러올 수 없습니다</p>
        <p className="text-xs text-[#92400E] mt-1">{error.message}</p>
      </div>
    );
  }
  if (!data || !data.found) {
    return (
      <div className="bg-[#FFF7ED] border border-[#FED7AA] rounded-2xl p-5">
        <p className="text-sm font-semibold text-[#92400E]">
          ⚠️ {data?.found === false ? data.reason : "잔고 없음"}
        </p>
      </div>
    );
  }

  const up = data.pnl >= 0;
  const color = up ? "#F04452" : "#1677FF";

  return (
    <div className="bg-white rounded-2xl p-5 shadow-card border border-border">
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm font-bold text-[#191F28]">내 모의투자</p>
        <span className="text-xs text-[#9CA3AF]">가상자금 · 한투 vps</span>
      </div>

      <div className="grid grid-cols-3 gap-3 mb-4">
        <div className="bg-[#F9FAFB] rounded-xl p-3">
          <p className="text-xs text-[#9CA3AF] mb-1 flex items-center gap-1">
            예수금 <GlossaryTooltip term="예수금" />
          </p>
          <p className="text-sm font-semibold text-[#191F28]">{fmt(data.cash)}</p>
        </div>
        <div className="bg-[#F9FAFB] rounded-xl p-3">
          <p className="text-xs text-[#9CA3AF] mb-1 flex items-center gap-1">
            총 평가금액 <GlossaryTooltip term="평가금액" />
          </p>
          <p className="text-sm font-semibold text-[#191F28]">{fmt(data.eval_amount)}</p>
        </div>
        <div className="bg-[#F9FAFB] rounded-xl p-3">
          <p className="text-xs text-[#9CA3AF] mb-1 flex items-center gap-1">
            평가손익 <GlossaryTooltip term="평가손익" />
          </p>
          <p className="text-sm font-semibold" style={{ color }}>
            {up ? "+" : ""}
            {fmt(data.pnl)}
          </p>
          <p className="text-xs font-medium" style={{ color }}>
            {up ? "+" : ""}
            {data.pnl_rate}%
          </p>
        </div>
      </div>

      {data.positions.length === 0 ? (
        <p className="text-xs text-[#9CA3AF] text-center py-3">
          보유 종목이 없습니다. 오른쪽에서 첫 모의 매수를 해보세요.
        </p>
      ) : (
        <div className="space-y-2">
          <p className="text-xs font-semibold text-[#6B7280] uppercase tracking-wider">보유 종목</p>
          {data.positions.map((p) => {
            const pu = p.pnl >= 0;
            const pc = pu ? "#F04452" : "#1677FF";
            return (
              <div
                key={p.ticker}
                className="flex items-center justify-between bg-[#F9FAFB] rounded-xl px-3 py-2.5"
              >
                <div>
                  <p className="text-sm font-medium text-[#191F28]">{p.name}</p>
                  <p className="text-xs text-[#9CA3AF]">
                    {p.qty}주 · 평균 {fmt(p.avg_price)}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-semibold text-[#191F28]">{fmt(p.eval_amount)}</p>
                  <p className="text-xs font-medium" style={{ color: pc }}>
                    {pu ? "+" : ""}
                    {fmt(p.pnl)} ({pu ? "+" : ""}
                    {p.pnl_rate}%)
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
