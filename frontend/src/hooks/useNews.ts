"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchNews } from "@/lib/api";
import type { NewsResponse } from "@/lib/types";

export function useNews(company: string) {
  return useQuery<NewsResponse, Error>({
    queryKey: ["news", company],
    queryFn: () => fetchNews(company),
    enabled: !!company,
    staleTime: 1000 * 60 * 5, // 5분 (백엔드도 10분 TTL 캐시)
    retry: 1,
  });
}
