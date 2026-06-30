// 재무 수치 포맷 유틸리티

export function formatKRW(value: number): string {
  const abs = Math.abs(value);
  const sign = value < 0 ? "-" : "";
  if (abs >= 1_0000_0000_0000) {
    return `${sign}${(abs / 1_0000_0000_0000).toFixed(1)}조`;
  }
  if (abs >= 1_0000_0000) {
    return `${sign}${Math.round(abs / 1_0000_0000).toLocaleString("ko-KR")}억`;
  }
  return value.toLocaleString("ko-KR");
}

export function formatKRWFull(value: number): string {
  return value.toLocaleString("ko-KR");
}

export function formatPct(pct: number | null): string {
  if (pct === null) return "—";
  const sign = pct >= 0 ? "+" : "";
  return `${sign}${pct}%`;
}

export function formatChange(delta: number, pct: number | null): string {
  const arrow = delta >= 0 ? "▲" : "▼";
  const sign = delta >= 0 ? "+" : "";
  return `${arrow} ${sign}${formatKRW(Math.abs(delta))} (${formatPct(pct)})`;
}

export function fsDivLabel(fsDiv: string): string {
  if (fsDiv === "CFS") return "연결재무제표";
  if (fsDiv === "OFS") return "별도재무제표";
  if (fsDiv === "MIXED") return "연결/별도 혼합";
  return fsDiv;
}
