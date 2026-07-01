"use client";

import { useState } from "react";
import { usePlaceOrder } from "@/hooks/usePaper";
import { useTradeJournal } from "@/hooks/useTradeJournal";

interface Props {
  company: string;
  currentPrice?: number;
  heldQty: number; // 현재 종목 보유 수량(0이면 매도 불가)
}

export function OrderPanel({ company, currentPrice, heldQty }: Props) {
  const [side, setSide] = useState<"buy" | "sell">("buy");
  const [qty, setQty] = useState(1);
  const [reason, setReason] = useState("");
  const { mutate, data, isPending, reset } = usePlaceOrder();
  const { addEntry } = useTradeJournal();

  const canSell = heldQty > 0;
  // 파생 상태로 계산 — heldQty/side가 바뀌어도 useEffect 없이 항상 일관됨
  // (보유가 없어지면 자동으로 매수로 취급, 수량은 보유분 이내로 자동 클램프)
  const isBuy = canSell ? side === "buy" : true;
  const qtyLimit = isBuy ? undefined : Math.max(heldQty, 1);
  const displayQty = qtyLimit !== undefined ? Math.min(Math.max(qty, 1), qtyLimit) : Math.max(qty, 1);

  const accent = isBuy ? "#F04452" : "#1677FF";
  const estimate = currentPrice ? currentPrice * displayQty : 0;

  const setClamped = (next: number) => {
    const v = Math.max(1, next);
    setQty(qtyLimit !== undefined ? Math.min(v, qtyLimit) : v);
  };

  const submit = () => {
    if (displayQty < 1 || isPending) return;
    if (!isBuy && displayQty > heldQty) return;
    const orderReason = reason.trim();
    mutate(
      { company, side: isBuy ? "buy" : "sell", qty: displayQty, order_type: "01", price: 0 },
      {
        onSuccess: (result) => {
          if (result.ok) {
            addEntry({
              company,
              side: isBuy ? "buy" : "sell",
              qty: displayQty,
              price: currentPrice ?? 0,
              reason: orderReason,
            });
            setReason("");
          }
        },
      },
    );
  };

  return (
    <div className="bg-white rounded-2xl p-5 shadow-card border border-border">
      <div className="flex items-center justify-between mb-3">
        <p className="text-sm font-bold text-[#191F28]">모의 주문</p>
        {canSell && <span className="text-xs text-[#6B7280]">보유 {heldQty}주</span>}
      </div>

      {/* 매수/매도 탭 — 매도는 보유 시에만 */}
      <div className="grid grid-cols-2 gap-1 bg-[#F2F4F6] rounded-xl p-1 mb-4">
        <button
          type="button"
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
          type="button"
          onClick={() => {
            if (!canSell) return;
            setSide("sell");
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
      <div className="text-xs text-[#6B7280] mb-1 flex items-center justify-between">
        <span>수량</span>
        {!isBuy && (
          <button
            type="button"
            onClick={() => setQty(heldQty)}
            className="text-[11px] text-[#1677FF] font-medium hover:underline"
          >
            전량 ({heldQty}주)
          </button>
        )}
      </div>
      <div className="flex items-center gap-2 mb-3">
        <button
          type="button"
          onClick={() => setClamped(displayQty - 1)}
          className="w-9 h-9 rounded-lg border border-border text-[#6B7280] hover:bg-[#F9FAFB]"
        >
          −
        </button>
        <input
          type="number"
          min={1}
          max={qtyLimit}
          value={displayQty}
          onChange={(e) => setClamped(parseInt(e.target.value) || 1)}
          className="flex-1 min-w-0 text-center text-sm border border-border rounded-lg py-2 focus:outline-none focus:ring-2 focus:ring-[#3182F6]"
        />
        <button
          type="button"
          onClick={() => setClamped(displayQty + 1)}
          className="w-9 h-9 rounded-lg border border-border text-[#6B7280] hover:bg-[#F9FAFB]"
        >
          +
        </button>
      </div>

      {/* 예상 금액 */}
      <div className="flex justify-between text-xs text-[#6B7280] mb-3">
        <span>예상 금액 (시장가)</span>
        <span className="font-semibold text-[#191F28]">
          {estimate ? estimate.toLocaleString("ko-KR") + "원" : "—"}
        </span>
      </div>

      {/* 매매일지 — 이유 기록(선택) */}
      <label className="text-xs text-[#6B7280] mb-1 block">
        {isBuy ? "왜 사나요?" : "왜 파나요?"} <span className="text-[#D1D5DB]">(선택)</span>
      </label>
      <textarea
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        placeholder="예: 3분기 실적 발표 기대, 목표가 도달 등"
        rows={2}
        className="w-full text-xs border border-border rounded-lg px-2.5 py-2 mb-4 resize-none focus:outline-none focus:ring-2 focus:ring-[#3182F6] placeholder:text-[#D1D5DB]"
      />

      {/* 주문 버튼 */}
      <button
        type="button"
        onClick={submit}
        disabled={isPending || (!isBuy && !canSell)}
        className="w-full py-3 rounded-xl text-white font-bold disabled:opacity-50 transition-opacity"
        style={{ background: accent }}
      >
        {isPending ? "주문 중..." : `${company} ${displayQty}주 ${isBuy ? "매수" : "매도"}`}
      </button>

      {/* 결과 */}
      {data && (
        <p className={`text-xs mt-3 ${data.ok ? "text-[#16A34A]" : "text-[#92400E]"}`}>
          {data.ok
            ? `✓ ${data.message}${data.order_no ? ` (주문번호 ${data.order_no})` : ""} · 매매일지에 기록됨`
            : `⚠️ ${data.message}`}
        </p>
      )}

      <p className="text-[10px] text-[#9CA3AF] mt-3 leading-relaxed">
        가상 자금 모의투자 · 실제 체결·투자 아님. 시장가 주문으로 처리됩니다.
      </p>
    </div>
  );
}
