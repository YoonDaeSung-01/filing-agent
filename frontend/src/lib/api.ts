import type {
  AskRequest,
  AskResponse,
  BalanceResponse,
  IntradayResponse,
  NewsResponse,
  OrderRequest,
  OrderResult,
  SearchResult,
  StockPriceResponse,
  StockResponse,
  TrendResponse,
} from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

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
  years = "2022,2023,2024",
): Promise<TrendResponse> {
  const params = new URLSearchParams({ company, account, years });
  const res = await fetch(`${BASE_URL}/financial/trend?${params}`);
  if (!res.ok) throw new Error(`추이 API 오류: ${res.status}`);
  return res.json() as Promise<TrendResponse>;
}
