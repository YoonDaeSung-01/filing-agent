import { formatKRW, fsDivLabel } from "@/lib/format";
import type { SumFact } from "@/lib/types";

export function SumCard({ fact }: { fact: SumFact }) {
  return (
    <div className="bg-white rounded-2xl p-5 shadow-card border border-border">
      <div className="mb-3">
        <p className="text-xs font-semibold text-[#6B7280] uppercase tracking-wider">
          {fact.account} 합산
        </p>
        <p className="text-xs text-[#6B7280] mt-0.5">{fact.year}년</p>
      </div>

      <div className="space-y-2 mb-3">
        {fact.values.map((v) => (
          <div key={v.company} className="flex items-center justify-between text-sm">
            <span className="text-[#6B7280]">{v.company}</span>
            <span className="font-medium text-[#191F28]">{formatKRW(v.value)}원</span>
          </div>
        ))}
        <div className="border-t border-border pt-2 flex items-center justify-between">
          <span className="text-sm font-bold text-[#191F28]">합계</span>
          <div className="text-right">
            <span className="text-2xl font-bold text-[#3182F6]">
              {formatKRW(fact.total)}
            </span>
            <span className="text-sm text-[#6B7280] ml-1">원</span>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
          fact.fs_div === "MIXED"
            ? "bg-[#FFF7ED] text-[#EA580C]"
            : "bg-[#EBF3FF] text-[#3182F6]"
        }`}>
          {fsDivLabel(fact.fs_div)}
        </span>
        <span className="text-xs text-[#6B7280]">OpenDART</span>
      </div>
    </div>
  );
}
