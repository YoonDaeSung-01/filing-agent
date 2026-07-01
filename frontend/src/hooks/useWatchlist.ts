"use client";

import { useState, useEffect, useCallback } from "react";

export interface WatchlistItem {
  name: string;
  addedAt: number;
}

const STORAGE_KEY = "filing-agent-watchlist";
const MAX_ITEMS = 30;

export function useWatchlist() {
  const [items, setItems] = useState<WatchlistItem[]>([]);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) setItems(JSON.parse(raw));
    } catch {
      // localStorage 없는 환경에선 무시
    }
  }, []);

  const persist = useCallback((next: WatchlistItem[]) => {
    setItems(next);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    } catch {
      /* 무시 */
    }
  }, []);

  const isWatched = useCallback((name: string) => items.some((i) => i.name === name), [items]);

  const toggle = useCallback(
    (name: string) => {
      if (items.some((i) => i.name === name)) {
        persist(items.filter((i) => i.name !== name));
      } else {
        persist([{ name, addedAt: Date.now() }, ...items].slice(0, MAX_ITEMS));
      }
    },
    [items, persist],
  );

  const remove = useCallback(
    (name: string) => persist(items.filter((i) => i.name !== name)),
    [items, persist],
  );

  return { items, isWatched, toggle, remove };
}
