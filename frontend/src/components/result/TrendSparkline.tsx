"use client";

import { AreaChart, Area, ResponsiveContainer, Tooltip } from "recharts";
import type { TrendPoint } from "@/lib/types";
import { formatKRW } from "@/lib/format";

interface Props {
  points: TrendPoint[];
}

export function TrendSparkline({ points }: Props) {
  const valid = points.filter((p) => p.value !== null);
  if (valid.length < 2) return null;

  const data = valid.map((p) => ({ year: p.year, value: p.value! }));

  return (
    <ResponsiveContainer width="100%" height={48}>
      <AreaChart data={data} margin={{ top: 2, right: 0, bottom: 2, left: 0 }}>
        <defs>
          <linearGradient id="sparkGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#3182F6" stopOpacity={0.15} />
            <stop offset="95%" stopColor="#3182F6" stopOpacity={0} />
          </linearGradient>
        </defs>
        <Tooltip
          contentStyle={{
            background: "#fff",
            border: "1px solid #E5E8EB",
            borderRadius: 8,
            fontSize: 11,
            padding: "4px 8px",
          }}
          formatter={(v) => [formatKRW(Number(v)), ""]}
          labelFormatter={(l) => `${l}년`}
        />
        <Area
          type="monotone"
          dataKey="value"
          stroke="#3182F6"
          strokeWidth={1.5}
          fill="url(#sparkGradient)"
          dot={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
