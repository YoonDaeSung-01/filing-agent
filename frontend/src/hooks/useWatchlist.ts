"use client";

import { useCallback } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { addWatchlistDb, fetchWatchlistDb, removeWatchlistDb } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";

// 프론트 소비 컴포넌트(WatchlistBar 등)와의 호환을 위한 얕은 뷰 모델.
// 실체는 백엔드 DB(watchlist 테이블) — AP-3.
export interface WatchlistItem {
  name: string;
  addedAt: number;
}

export function useWatchlist() {
  const { isAuthenticated } = useAuth();
  const router = useRouter();
  const qc = useQueryClient();

  const query = useQuery({
    queryKey: ["watchlist-db"],
    queryFn: fetchWatchlistDb,
    enabled: isAuthenticated,
  });

  const items: WatchlistItem[] = (query.data ?? []).map((w) => ({
    name: w.company,
    addedAt: Date.parse(w.created_at) || 0, // 파싱 실패 시 0(정상 응답이면 발생 안 함) — 렌더 중 비순수 호출 방지
  }));

  const invalidate = () => qc.invalidateQueries({ queryKey: ["watchlist-db"] });

  const addMutation = useMutation({
    mutationFn: (company: string) => addWatchlistDb(company),
    onSuccess: invalidate,
  });

  const removeByCompany = useMutation({
    mutationFn: async (company: string) => {
      const found = (query.data ?? []).find((w) => w.company === company);
      if (found) await removeWatchlistDb(found.id);
    },
    onSuccess: invalidate,
  });

  const isWatched = useCallback(
    (name: string) => items.some((i) => i.name === name),
    [items],
  );

  const toggle = useCallback(
    (name: string) => {
      if (!isAuthenticated) {
        router.push("/login");
        return;
      }
      if (isWatched(name)) removeByCompany.mutate(name);
      else addMutation.mutate(name);
    },
    [isAuthenticated, isWatched, addMutation, removeByCompany, router],
  );

  const remove = useCallback(
    (name: string) => {
      if (!isAuthenticated) return;
      removeByCompany.mutate(name);
    },
    [isAuthenticated, removeByCompany],
  );

  return { items, isWatched, toggle, remove, isAuthenticated };
}
