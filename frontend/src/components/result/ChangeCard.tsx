import { formatKRW, formatPct, fsDivLabel } from "@/lib/format";
import type { ChangeFact } from "@/lib/types";

export function ChangeCard({ fact }: { fact: ChangeFact }) {
  const isUp = fact.delta >= 0;

  return (
    <div className="bg-white rounded-2xl p-5 shadow-card border border-border">
      <div className="mb-3">
        <p className="text-xs font-semibold text-[#6B7280] uppercase tracking-wider">
          {fact.account} 증감
        </p>
        <p className="text-xs text-[#6B7280] mt-0.5">
          {fact.year_from} → {fact.year_to}년
        </p>
      </div>

      <div className="flex items-baseline gap-2 mb-1">
        <span
          className={`text-3xl font-bold tracking-tight ${
            isUp ? "text-[#F04452]" : "text-[#1677FF]"
          }`}
        >
          {isUp ? "▲" : "▼"} {formatKRW(Math.abs(fact.delta))}
        </span>
        <span className="text-sm font-medium text-[#6B7280]">원</span>
      </div>

      <p
        className={`text-lg font-semibold mb-3 ${
          isUp ? "text-[#F04452]" : "text-[#1677FF]"
        }`}
      >
        {isUp ? "+" : ""}{formatPct(fact.pct_change)}
      </p>

      <div className="flex gap-4 text-xs text-[#6B7280] border-t border-border pt-3">
        <div>
          <p className="font-medium">전기 ({fact.year_from})</p>
          <p>{formatKRW(fact.value_from)}원</p>
        </div>
        <div className="text-[#D1D5DB]">→</div>
        <div>
          <p className="font-medium">당기 ({fact.year_to})</p>
          <p>{formatKRW(fact.value_to)}원</p>
        </div>
      </div>

      <div className="flex items-center gap-2 mt-3">
        <span className="text-xs bg-[#EBF3FF] text-[#3182F6] px-2 py-0.5 rounded-full font-medium">
          {fsDivLabel(fact.fs_div)}
        </span>
        <span className="text-xs text-[#6B7280]">OpenDART</span>
      </div>
    </div>
  );
}
