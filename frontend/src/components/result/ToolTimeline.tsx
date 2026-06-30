"use client";

import { TOOL_LABELS } from "@/lib/constants";
import type { ToolLogEntry } from "@/lib/types";

const TOOL_ICONS: Record<string, string> = {
  financial_lookup: "📊",
  compute_change: "📈",
  compute_sum: "➕",
  doc_search: "📄",
};

interface ToolTimelineProps {
  toolLog: ToolLogEntry[];
}

function formatArgs(tool: string, args: Record<string, unknown>): string {
  if (tool === "financial_lookup") {
    return `${args.company} · ${args.account} · ${args.year}년`;
  }
  if (tool === "compute_change") {
    return `${args.company} · ${args.account} · ${args.year_from}→${args.year_to}`;
  }
  if (tool === "compute_sum") {
    const companies = Array.isArray(args.companies) ? args.companies.join(", ") : "";
    return `${companies} · ${args.account} · ${args.year}년`;
  }
  if (tool === "doc_search") {
    const q = String(args.query ?? "");
    return q.length > 30 ? q.slice(0, 30) + "…" : q;
  }
  return "";
}

export function ToolTimeline({ toolLog }: ToolTimelineProps) {
  if (toolLog.length === 0) return null;

  return (
    <div className="space-y-1.5">
      <p className="text-xs font-semibold text-[#6B7280] uppercase tracking-wider">
        도구 실행
      </p>
      <div className="space-y-1">
        {toolLog.map((entry, i) => (
          <div
            key={i}
            className="flex items-center gap-2.5 px-3 py-2 bg-[#F2F4F6] rounded-xl text-sm"
          >
            <span className="text-base">{TOOL_ICONS[entry.tool] ?? "🔧"}</span>
            <span className="font-medium text-[#191F28]">
              {TOOL_LABELS[entry.tool] ?? entry.tool}
            </span>
            <span className="text-[#6B7280] flex-1 truncate text-xs">
              {formatArgs(entry.tool, entry.args)}
            </span>
            <span
              className={`text-xs font-semibold ${
                entry.ok ? "text-[#16A34A]" : "text-[#F04452]"
              }`}
            >
              {entry.ok ? "✓" : "✗"}
            </span>
            {entry.ms !== undefined && (
              <span className="text-xs text-[#6B7280]">{entry.ms}ms</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
