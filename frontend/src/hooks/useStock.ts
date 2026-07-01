"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchStock, fetchStockPrice, fetchIntraday, fetchFinancialTrend } from "@/lib/api";
import type {
  IntradayResponse,
  StockPriceResponse,
  StockResponse,
  TrendResponse,
} from "@/lib/types";

// 당일 분봉(실시간/1일 차트) — 활성 시 30초 갱신
export function useIntraday(company: string, enabled: boolean) {
  return useQuery<IntradayResponse, Error>({
    queryKey: ["intraday", company],
    queryFn: () => fetchIntraday(company),
    enabled: enabled && !!company,
    refetchInterval: enabled ? 30000 : false,
    staleTime: 0,
    retry: 1,
  });
}

// 한투 실시간 현재가 — 5초 폴링(실시간 근사)
export function useStockPrice(company: string) {
  return useQuery<StockPriceResponse, Error>({
    queryKey: ["stock-price", company],
    queryFn: () => fetchStockPrice(company),
    enabled: !!company,
    refetchInterval: 5000,
    staleTime: 0,
    retry: 1,
  });
}

export function useStock(company: string, period = 365, enabled = true) {
  return useQuery<StockResponse, Error>({
    queryKey: ["stock", company, period],
    queryFn: () => fetchStock(company, period),
    enabled: enabled && !!company,
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
