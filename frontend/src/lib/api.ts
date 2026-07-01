import type {
  AskRequest,
  AskResponse,
  BalanceResponse,
  IntradayResponse,
  JournalEntryDto,
  MarketMoversResponse,
  MarketSectorsResponse,
  MeResponse,
  NewsResponse,
  OrderRequest,
  OrderResult,
  SearchResult,
  StockPriceResponse,
  StockResponse,
  TokenResponse,
  TrendResponse,
  WatchlistItemDto,
} from "./types";
import { authHeaders } from "./auth";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function parseError(res: Response, fallback: string): Promise<never> {
  let detail: string | undefined;
  try {
    const body = await res.json();
    detail = body?.detail;
  } catch {
    // 응답 본문이 JSON이 아니면 detail 없이 fallback 사용
  }
  throw new Error(detail || fallback);
}

export async function ask(req: AskRequest): Promise<AskResponse> {
  const res = await fetch(`${BASE_URL}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });

  if (!res.ok) {
    throw new Error(`API 오류: ${res.status} ${res.statusText}`);
  }

  return res.json() as Promise<AskResponse>;
}

export async function healthCheck(): Promise<boolean> {
  try {
    const res = await fetch(`${BASE_URL}/health`);
    return res.ok;
  } catch {
    return false;
  }
}

export async function fetchStock(company: string, period = 365): Promise<StockResponse> {
  const params = new URLSearchParams({ company, period: String(period) });
  const res = await fetch(`${BASE_URL}/stock?${params}`);
  if (!res.ok) throw new Error(`주가 API 오류: ${res.status}`);
  return res.json() as Promise<StockResponse>;
}

export async function fetchStockPrice(company: string): Promise<StockPriceResponse> {
  const res = await fetch(`${BASE_URL}/stock/price?company=${encodeURIComponent(company)}`);
  if (!res.ok) throw new Error(`현재가 API 오류: ${res.status}`);
  return res.json() as Promise<StockPriceResponse>;
}

export async function fetchMarketMovers(): Promise<MarketMoversResponse> {
  const res = await fetch(`${BASE_URL}/market/movers`);
  if (!res.ok) throw new Error(`시장 순위 API 오류: ${res.status}`);
  return res.json() as Promise<MarketMoversResponse>;
}

export async function fetchMarketSectors(): Promise<MarketSectorsResponse> {
  const res = await fetch(`${BASE_URL}/market/sectors`);
  if (!res.ok) throw new Error(`분야별 시세 API 오류: ${res.status}`);
  return res.json() as Promise<MarketSectorsResponse>;
}

export async function fetchNews(company: string, display = 8): Promise<NewsResponse> {
  const params = new URLSearchParams({ company, display: String(display) });
  const res = await fetch(`${BASE_URL}/news?${params}`);
  if (!res.ok) throw new Error(`뉴스 API 오류: ${res.status}`);
  return res.json() as Promise<NewsResponse>;
}

export async function fetchIntraday(company: string): Promise<IntradayResponse> {
  const res = await fetch(`${BASE_URL}/stock/intraday?company=${encodeURIComponent(company)}`);
  if (!res.ok) throw new Error(`분봉 API 오류: ${res.status}`);
  return res.json() as Promise<IntradayResponse>;
}

export async function searchStocks(q: string): Promise<SearchResult[]> {
  if (!q.trim()) return [];
  const res = await fetch(`${BASE_URL}/stock/search?q=${encodeURIComponent(q)}&limit=8`);
  if (!res.ok) return [];
  const data = (await res.json()) as { results?: SearchResult[] };
  return data.results ?? [];
}

export async function fetchBalance(): Promise<BalanceResponse> {
  const res = await fetch(`${BASE_URL}/paper/balance`);
  if (!res.ok) throw new Error(`잔고 API 오류: ${res.status}`);
  return res.json() as Promise<BalanceResponse>;
}

export async function placeOrder(req: OrderRequest): Promise<OrderResult> {
  const res = await fetch(`${BASE_URL}/paper/order`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error(`주문 API 오류: ${res.status}`);
  return res.json() as Promise<OrderResult>;
}

export async function fetchFinancialTrend(
  company: string,
  account: string,
  years = "2023,2024,2025",
): Promise<TrendResponse> {
  const params = new URLSearchParams({ company, account, years });
  const res = await fetch(`${BASE_URL}/financial/trend?${params}`);
  if (!res.ok) throw new Error(`추이 API 오류: ${res.status}`);
  return res.json() as Promise<TrendResponse>;
}

// ── 인증 ─────────────────────────────────────────────────────────────────────

export async function registerAccount(
  username: string,
  name: string,
  password: string,
): Promise<TokenResponse> {
  const res = await fetch(`${BASE_URL}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, name, password }),
  });
  if (!res.ok) return parseError(res, "회원가입에 실패했습니다.");
  return res.json() as Promise<TokenResponse>;
}

export async function loginAccount(username: string, password: string): Promise<TokenResponse> {
  const res = await fetch(`${BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) return parseError(res, "로그인에 실패했습니다.");
  return res.json() as Promise<TokenResponse>;
}

export async function fetchMe(): Promise<MeResponse> {
  const res = await fetch(`${BASE_URL}/auth/me`, { headers: authHeaders() });
  if (!res.ok) throw new Error("인증 정보를 확인할 수 없습니다.");
  return res.json() as Promise<MeResponse>;
}

// ── 관심종목 (백엔드 DB) ─────────────────────────────────────────────────────

export async function fetchWatchlistDb(): Promise<WatchlistItemDto[]> {
  const res = await fetch(`${BASE_URL}/watchlist`, { headers: authHeaders() });
  if (!res.ok) throw new Error("관심종목을 불러올 수 없습니다.");
  return res.json() as Promise<WatchlistItemDto[]>;
}

export async function addWatchlistDb(
  company: string,
  ticker?: string | null,
): Promise<{ id: number; company: string }> {
  const res = await fetch(`${BASE_URL}/watchlist`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ company, ticker: ticker ?? null }),
  });
  if (!res.ok) return parseError(res, "관심종목 추가에 실패했습니다.");
  return res.json();
}

export async function removeWatchlistDb(id: number): Promise<void> {
  const res = await fetch(`${BASE_URL}/watchlist/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!res.ok && res.status !== 204) throw new Error("관심종목 삭제에 실패했습니다.");
}

// ── 매매일지 (백엔드 DB) ─────────────────────────────────────────────────────

export async function fetchJournalDb(): Promise<JournalEntryDto[]> {
  const res = await fetch(`${BASE_URL}/journal`, { headers: authHeaders() });
  if (!res.ok) throw new Error("매매일지를 불러올 수 없습니다.");
  return res.json() as Promise<JournalEntryDto[]>;
}

export async function addJournalDb(entry: {
  company: string;
  side: "buy" | "sell";
  qty: number;
  price?: number;
  reason?: string;
}): Promise<{ id: number }> {
  const res = await fetch(`${BASE_URL}/journal`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(entry),
  });
  if (!res.ok) return parseError(res, "매매일지 저장에 실패했습니다.");
  return res.json();
}
