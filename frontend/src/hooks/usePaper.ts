"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchBalance, placeOrder } from "@/lib/api";
import type { BalanceResponse, OrderRequest, OrderResult } from "@/lib/types";

// 모의투자 잔고 — 10초 폴링(주문 후 반영 확인)
export function useBalance() {
  return useQuery<BalanceResponse, Error>({
    queryKey: ["paper-balance"],
    queryFn: fetchBalance,
    refetchInterval: 10000,
    staleTime: 0,
  });
}

// 모의 주문 — 성공 시 잔고 즉시 갱신
export function usePlaceOrder() {
  const qc = useQueryClient();
  return useMutation<OrderResult, Error, OrderRequest>({
    mutationFn: placeOrder,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["paper-balance"] });
    },
  });
}
