"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchStock, fetchFinancialTrend } from "@/lib/api";
import type { StockResponse, TrendResponse } from "@/lib/types";

export function useStock(company: string, period = 365) {
  return useQuery<StockResponse, Error>({
    queryKey: ["stock", company, period],
    queryFn: () => fetchStock(company, period),
    enabled: !!company,
    staleTime: 1000 * 60 * 10, // 10분 캐시
    retry: 1,
  });
}

export function useFinancialTrend(
  company: string,
  account: string,
  years = "2022,2023,2024",
  enabled = true,
) {
  return useQuery<TrendResponse, Error>({
    queryKey: ["financial-trend", company, account, years],
    queryFn: () => fetchFinancialTrend(company, account, years),
    enabled: enabled && !!company && !!account,
    staleTime: 1000 * 60 * 60, // 1시간 캐시 (재무 데이터는 자주 안 바뀜)
    retry: 1,
  });
}
