"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchMarketMovers, fetchMarketSectors } from "@/lib/api";
import type { MarketMoversResponse, MarketSectorsResponse } from "@/lib/types";

// 시장 전체 순위 + 관심 종목 분야별 시세 — 무거운 조회라 폴링은 넉넉하게(1분)
export function useMarketMovers() {
  return useQuery<MarketMoversResponse, Error>({
    queryKey: ["market-movers"],
    queryFn: fetchMarketMovers,
    refetchInterval: 60000,
    staleTime: 30000,
    retry: 1,
  });
}

export function useMarketSectors() {
  return useQuery<MarketSectorsResponse, Error>({
    queryKey: ["market-sectors"],
    queryFn: fetchMarketSectors,
    refetchInterval: 60000,
    staleTime: 30000,
    retry: 1,
  });
}
