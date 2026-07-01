"use client";

import { useState } from "react";
import { usePlaceOrder } from "@/hooks/usePaper";

interface Props {
  company: string;
  currentPrice?: number;
}

export function OrderPanel({ company, currentPrice }: Props) {
  const [side, setSide] = useState<"buy" | "sell">("buy");
  const [qty, setQty] = useState(1);
  const { mutate, data, isPending, reset } = usePlaceOrder();

  const isBuy = side === "buy";
  const accent = isBuy ? "#F04452" : "#1677FF";
  const estimate = currentPrice ? currentPrice * qty : 0;

  const submit = () => {
    if (qty < 1 || isPending) return;
    mutate({ company, side, qty, order_type: "01", price: 0 });
  };

  return (
    <div className="bg-white rounded-2xl p-5 shadow-card border border-border">
      <p className="text-sm font-bold text-[#191F28] mb-3">모의 주문</p>

      {/* 매수/매도 탭 */}
      <div className="grid grid-cols-2 gap-1 bg-[#F2F4F6] rounded-xl p-1 mb-4">
        {(["buy", "sell"] as const).map((s) => (
          <button
            key={s}
            onClick={() => {
              setSide(s);
              reset();
            }}
            className={`py-2 text-sm font-semibold rounded-lg transition-colors ${
              side === s
                ? s === "buy"
                  ? "bg-[#F04452] text-white"
                  : "bg-[#1677FF] text-white"
                : "text-[#6B7280]"
            }`}
          >
            {s === "buy" ? "매수" : "매도"}
          </button>
        ))}
      </div>

      {/* 수량 */}
      <label className="text-xs text-[#6B7280] mb-1 block">수량</label>
      <div className="flex items-center gap-2 mb-3">
        <button
          onClick={() => setQty((q) => Math.max(1, q - 1))}
          className="w-9 h-9 rounded-lg border border-border text-[#6B7280] hover:bg-[#F9FAFB]"
        >
          −
        </button>
        <input
          type="number"
          min={1}
          value={qty}
          onChange={(e) => setQty(Math.max(1, parseInt(e.target.value) || 1))}
          className="flex-1 min-w-0 text-center text-sm border border-border rounded-lg py-2 focus:outline-none focus:ring-2 focus:ring-[#3182F6]"
        />
        <button
          onClick={() => setQty((q) => q + 1)}
          className="w-9 h-9 rounded-lg border border-border text-[#6B7280] hover:bg-[#F9FAFB]"
        >
          +
        </button>
      </div>

      {/* 예상 금액 */}
      <div className="flex justify-between text-xs text-[#6B7280] mb-4">
        <span>예상 금액 (시장가)</span>
        <span className="font-semibold text-[#191F28]">
          {estimate ? estimate.toLocaleString("ko-KR") + "원" : "—"}
        </span>
      </div>

      {/* 주문 버튼 */}
      <button
        onClick={submit}
        disabled={isPending}
        className="w-full py-3 rounded-xl text-white font-bold disabled:opacity-50 transition-opacity"
        style={{ background: accent }}
      >
        {isPending ? "주문 중..." : `${company} ${qty}주 ${isBuy ? "매수" : "매도"}`}
      </button>

      {/* 결과 */}
      {data && (
        <p className={`text-xs mt-3 ${data.ok ? "text-[#16A34A]" : "text-[#92400E]"}`}>
          {data.ok
            ? `✓ ${data.message}${data.order_no ? ` (주문번호 ${data.order_no})` : ""}`
            : `⚠️ ${data.message}`}
        </p>
      )}

      <p className="text-[10px] text-[#9CA3AF] mt-3 leading-relaxed">
        가상 자금 모의투자 · 실제 체결·투자 아님. 시장가 주문으로 처리됩니다.
      </p>
    </div>
  );
}
