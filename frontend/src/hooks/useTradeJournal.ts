"use client";

import { useState, useEffect, useCallback } from "react";

export interface JournalEntry {
  id: string;
  company: string;
  side: "buy" | "sell";
  qty: number;
  price: number; // 주문 시점 참고가(시장가 예상금액 기준)
  reason: string;
  createdAt: number;
}

const STORAGE_KEY = "filing-agent-journal";
const MAX_ITEMS = 100;

export function useTradeJournal() {
  const [entries, setEntries] = useState<JournalEntry[]>([]);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) setEntries(JSON.parse(raw));
    } catch {
      // localStorage 없는 환경에선 무시
    }
  }, []);

  const addEntry = useCallback((entry: Omit<JournalEntry, "id" | "createdAt">) => {
    const item: JournalEntry = {
      ...entry,
      id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
      createdAt: Date.now(),
    };
    setEntries((prev) => {
      const next = [item, ...prev].slice(0, MAX_ITEMS);
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      } catch {
        /* 무시 */
      }
      return next;
    });
  }, []);

  return { entries, addEntry };
}
