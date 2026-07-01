"use client";

import { useState } from "react";
import { BookText } from "lucide-react";
import { useTradeJournal } from "@/hooks/useTradeJournal";

function fmt(v: number) {
  return v.toLocaleString("ko-KR");
}

function fmtDate(ts: number) {
  return new Date(ts).toLocaleString("ko-KR", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function JournalCard() {
  const { entries } = useTradeJournal();
  const [open, setOpen] = useState(false);

  if (entries.length === 0) return null;

  const visible = open ? entries : entries.slice(0, 3);

  return (
    <div className="bg-white rounded-2xl p-5 shadow-card border border-border">
      <div className="flex items-center gap-2 mb-3">
        <BookText size={15} className="text-[#6B7280]" />
        <p className="text-sm font-bold text-[#191F28]">매매일지</p>
        <span className="text-xs text-[#9CA3AF]">{entries.length}건</span>
      </div>

      <div className="space-y-2">
        {visible.map((e) => {
          const isBuy = e.side === "buy";
          const color = isBuy ? "#F04452" : "#1677FF";
          return (
            <div key={e.id} className="bg-[#F9FAFB] rounded-xl px-3 py-2.5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span
                    className="text-xs font-bold px-1.5 py-0.5 rounded"
                    style={{ color, background: isBuy ? "#FFF0F0" : "#EBF3FF" }}
                  >
                    {isBuy ? "매수" : "매도"}
                  </span>
                  <span className="text-sm font-medium text-[#191F28]">{e.company}</span>
                  <span className="text-xs text-[#9CA3AF]">{e.qty}주</span>
                </div>
                <span className="text-xs text-[#9CA3AF]">{fmtDate(e.createdAt)}</span>
              </div>
              {e.price > 0 && (
                <p className="text-xs text-[#9CA3AF] mt-1">참고가 {fmt(e.price)}원</p>
              )}
              {e.reason && (
                <p className="text-xs text-[#191F28] mt-1.5 leading-relaxed">{e.reason}</p>
              )}
            </div>
          );
        })}
      </div>

      {entries.length > 3 && (
        <button
          onClick={() => setOpen((v) => !v)}
          className="w-full text-center text-xs text-[#3182F6] font-medium mt-3 hover:underline"
        >
          {open ? "접기" : `전체 ${entries.length}건 보기`}
        </button>
      )}
    </div>
  );
}
