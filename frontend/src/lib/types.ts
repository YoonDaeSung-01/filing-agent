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
