"use client";

import { useEffect, useState } from "react";
import { usePlaceOrder } from "@/hooks/usePaper";

interface Props {
  company: string;
  currentPrice?: number;
  heldQty: number; // 현재 종목 보유 수량(0이면 매도 불가)
}

export function OrderPanel({ company, currentPrice, heldQty }: Props) {
  const [side, setSide] = useState<"buy" | "sell">("buy");
  const [qty, setQty] = useState(1);
  const { mutate, data, isPending, reset } = usePlaceOrder();

  const canSell = heldQty > 0;

  // 보유가 없어지면(또는 없는 종목이면) 매수로 강제 전환
  useEffect(() => {
    if (!canSell && side === "sell") setSide("buy");
  }, [canSell, side]);

  // 매도 수량은 보유분까지만
  useEffect(() => {
    if (side === "sell" && qty > heldQty) setQty(Math.max(1, heldQty));
  }, [side, heldQty, qty]);

  const isBuy = side === "buy";
  const accent = isBuy ? "#F04452" : "#1677FF";
  const estimate = currentPrice ? currentPrice * qty : 0;
  const maxQty = isBuy ? undefined : heldQty;

  const submit = () => {
    if (qty < 1 || isPending) return;
    if (!isBuy && qty > heldQty) return;
    mutate({ company, side, qty, order_type: "01", price: 0 });
  };

  return (
    <div className="bg-white rounded-2xl p-5 shadow-card border border-border">
      <div className="flex items-center justify-between mb-3">
        <p className="text-sm font-bold text-[#191F28]">모의 주문</p>
        {canSell && (
          <span className="text-xs text-[#6B7280]">보유 {heldQty}주</span>
        )}
      </div>

      {/* 매수/매도 탭 — 매도는 보유 시에만 */}
      <div className="grid grid-cols-2 gap-1 bg-[#F2F4F6] rounded-xl p-1 mb-4">
        <button
          onClick={() => {
            setSide("buy");
            reset();
          }}
          className={`py-2 text-sm font-semibold rounded-lg transition-colors ${
            isBuy ? "bg-[#F04452] text-white" : "text-[#6B7280]"
          }`}
        >
          매수
        </button>
        <button
          onClick={() => {
            if (!canSell) return;
            setSide("sell");
            setQty(Math.min(qty, heldQty) || 1);
            reset();
          }}
          disabled={!canSell}
          title={canSell ? "" : "보유 종목만 매도할 수 있습니다"}
          className={`py-2 text-sm font-semibold rounded-lg transition-colors ${
            !isBuy
              ? "bg-[#1677FF] text-white"
              : canSell
                ? "text-[#6B7280]"
                : "text-[#D1D5DB] cursor-not-allowed"
          }`}
        >
          매도
        </button>
      </div>

      {/* 수량 */}
      <label className="text-xs text-[#6B7280] mb-1 flex items-center justify-between">
        <span>수량</span>
        {!isBuy && (
          <button
            onClick={() => setQty(heldQty)}
            className="text-[11px] text-[#1677FF] font-medium hover:underline"
          >
            전량 ({heldQty}주)
          </button>
        )}
      </label>
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
          max={maxQty}
          value={qty}
          onChange={(e) => {
            let v = Math.max(1, parseInt(e.target.value) || 1);
            if (maxQty !== undefined) v = Math.min(v, maxQty);
            setQty(v);
          }}
          className="flex-1 min-w-0 text-center text-sm border border-border rounded-lg py-2 focus:outline-none focus:ring-2 focus:ring-[#3182F6]"
        />
        <button
          onClick={() => setQty((q) => (maxQty !== undefined ? Math.min(maxQty, q + 1) : q + 1))}
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
        disabled={isPending || (!isBuy && !canSell)}
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
