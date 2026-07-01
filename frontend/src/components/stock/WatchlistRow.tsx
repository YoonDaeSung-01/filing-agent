"use client";

import Link from "next/link";
import { X } from "lucide-react";
import { useStockPrice } from "@/hooks/useStock";

function fmt(v: number) {
  return v.toLocaleString("ko-KR");
}

interface Props {
  company: string;
  onRemove: () => void;
}

export function WatchlistRow({ company, onRemove }: Props) {
  // 대시보드는 여러 종목을 한 번에 보므로 30초 간격(한투 호출량 보호)
  const { data, isLoading } = useStockPrice(company, 30000);

  return (
    <Link
      href={`/stocks?company=${encodeURIComponent(company)}`}
      className="flex items-center justify-between px-4 py-3.5 bg-white rounded-2xl border border-border shadow-card hover:border-[#3182F6] hover:shadow-card-hover transition-all group"
    >
      <div>
        <p className="text-sm font-bold text-[#191F28]">{company}</p>
        {data?.found && <p className="text-xs text-[#9CA3AF] mt-0.5">{data.ticker}</p>}
      </div>

      <div className="flex items-center gap-3">
        {isLoading && <div className="h-5 w-20 bg-[#F2F4F6] rounded animate-pulse" />}
        {data?.found && (
          <div className="text-right">
            <p className="text-sm font-semibold text-[#191F28]">{fmt(data.price)}원</p>
            <p
              className="text-xs font-medium"
              style={{ color: data.change >= 0 ? "#F04452" : "#1677FF" }}
            >
              {data.change >= 0 ? "+" : ""}
              {data.change_pct}%
            </p>
          </div>
        )}
        {data && !data.found && <p className="text-xs text-[#9CA3AF]">{data.reason}</p>}

        <button
          type="button"
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            onRemove();
          }}
          aria-label={`${company} 관심종목에서 제거`}
          className="p-1.5 rounded-full text-[#D1D5DB] opacity-0 group-hover:opacity-100 hover:bg-[#F2F4F6] hover:text-[#F04452] transition-all"
        >
          <X size={14} />
        </button>
      </div>
    </Link>
  );
}
