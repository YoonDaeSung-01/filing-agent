"use client";

import { useCallback } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { addJournalDb, fetchJournalDb } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";

// 프론트 소비 컴포넌트(JournalCard 등)와의 호환을 위한 얕은 뷰 모델.
// 실체는 백엔드 DB(trade_journal 테이블) — AP-3.
export interface JournalEntry {
  id: string;
  company: string;
  side: "buy" | "sell";
  qty: number;
  price: number;
  reason: string;
  createdAt: number;
}

export function useTradeJournal() {
  const { isAuthenticated } = useAuth();
  const qc = useQueryClient();

  const query = useQuery({
    queryKey: ["journal-db"],
    queryFn: fetchJournalDb,
    enabled: isAuthenticated,
  });

  const entries: JournalEntry[] = (query.data ?? []).map((e) => ({
    id: String(e.id),
    company: e.company,
    side: e.side,
    qty: e.qty,
    price: e.price,
    reason: e.reason,
    createdAt: Date.parse(e.created_at) || 0, // 파싱 실패 시 0 — 렌더 중 비순수 호출 방지
  }));

  const addMutation = useMutation({
    mutationFn: addJournalDb,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["journal-db"] }),
  });

  const addEntry = useCallback(
    (entry: Omit<JournalEntry, "id" | "createdAt">) => {
      if (!isAuthenticated) return; // 미로그인 시 조용히 스킵(주문 자체는 이미 완료된 뒤라 실패 처리 불필요)
      addMutation.mutate(entry);
    },
    [isAuthenticated, addMutation],
  );

  return { entries, addEntry, isAuthenticated };
}
