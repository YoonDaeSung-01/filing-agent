"use client";

import { useState, useEffect, useCallback } from "react";
import type { AskRequest } from "@/lib/types";

export interface HistoryItem {
  id: string;
  question: string;
  company?: string | null;
  year?: number | null;
  timestamp: number;
}

const STORAGE_KEY = "filing-agent-history";
const MAX_ITEMS = 20;

export function useQueryHistory() {
  const [history, setHistory] = useState<HistoryItem[]>([]);

  useEffect(() => {
    try {
      const raw = sessionStorage.getItem(STORAGE_KEY);
      if (raw) setHistory(JSON.parse(raw));
    } catch {
      // sessionStorage 없는 환경에선 무시
    }
  }, []);

  const addToHistory = useCallback((req: AskRequest) => {
    const item: HistoryItem = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
      question: req.question,
      company: req.company,
      year: req.year,
      timestamp: Date.now(),
    };
    setHistory((prev) => {
      const next = [item, ...prev].slice(0, MAX_ITEMS);
      try {
        sessionStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      } catch { /* 무시 */ }
      return next;
    });
  }, []);

  const clearHistory = useCallback(() => {
    setHistory([]);
    try { sessionStorage.removeItem(STORAGE_KEY); } catch { /* 무시 */ }
  }, []);

  return { history, addToHistory, clearHistory };
}
