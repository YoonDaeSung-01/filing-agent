import type { AskRequest, AskResponse, StockResponse, TrendResponse } from "./types";

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
