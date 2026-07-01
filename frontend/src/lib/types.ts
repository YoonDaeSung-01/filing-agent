// DART Filing Agent — 백엔드 API 계약 타입
// src/filing_agent/api/main.py AskRequest / AskResponse 와 1:1 대응

export interface AskRequest {
  question: string;
  company?: string | null;
  year?: number | null;
}

export interface AskResponse {
  answer: string;
  sources: string[];
  tool_log: ToolLogEntry[];
  facts: Fact[];
  status: "ok" | "blocked" | "failed";
}

export interface ToolLogEntry {
  tool: "doc_search" | "financial_lookup" | "compute_change" | "compute_sum";
  args: Record<string, unknown>;
  ok: boolean;
  ms?: number;
}

// facts 는 도구 모양으로 구분되는 판별 유니온
// graph.py _summarize_facts 와 동일 로직

export interface LookupFact {
  company: string;
  account: string;
  year: number;
  value: number;
  fs_div: "CFS" | "OFS";
  source: string;
}

export interface ChangeFact {
  company: string;
  account: string;
  year_from: number;
  value_from: number;
  year_to: number;
  value_to: number;
  delta: number;
  pct_change: number | null;
  fs_div: string;
  source: string;
}

export interface SumFact {
  companies: string[];
  account: string;
  year: number;
  values: { company: string; value: number }[];
  total: number;
  fs_div: "CFS" | "OFS" | "MIXED";
  source: string[];
}

export type Fact = LookupFact | ChangeFact | SumFact;

export type FactKind = "lookup" | "change" | "sum";

export function factKind(f: Fact): FactKind {
  if ("total" in f && "values" in f) return "sum";
  if ("delta" in f) return "change";
  return "lookup";
}

// ── 주가 데이터 타입 ────────────────────────────────────────────────────────

export interface OHLCPoint {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface StockSummary {
  found: true;
  company: string;
  ticker: string;
  date: string;
  close: number;
  change: number;
  change_pct: number | null;
  high_52w: number;
  low_52w: number;
  ohlc: OHLCPoint[];
}

export interface StockError {
  found: false;
  reason: string;
}

export type StockResponse = StockSummary | StockError;

// 한투 KIS 실시간 현재가 (사실만; PER/PBR 등 해석지표 제외)
export interface StockPrice {
  found: true;
  company: string;
  ticker: string;
  price: number;
  change: number;       // 부호 포함
  change_pct: number;
  open: number;
  high: number;
  low: number;
  volume: number;
  market_cap_eok: number; // 시가총액(억원)
  w52_high: number;
  w52_low: number;
}

export type StockPriceResponse = StockPrice | StockError;

// ── 재무 추이 타입 ──────────────────────────────────────────────────────────

export interface TrendPoint {
  year: number;
  value: number | null;
  fs_div: string | null;
}

export interface FinancialTrend {
  found: true;
  company: string;
  account: string;
  points: TrendPoint[];
}

export interface TrendError {
  found: false;
  reason: string;
}

export type TrendResponse = FinancialTrend | TrendError;
