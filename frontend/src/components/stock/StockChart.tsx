"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { OHLCPoint } from "@/lib/types";

function formatClose(v: number) {
  return v.toLocaleString("ko-KR") + "원";
}

function formatDate(dateStr: string) {
  const d = new Date(dateStr);
  return `${d.getMonth() + 1}/${d.getDate()}`;
}

interface Props {
  data: OHLCPoint[];
  period: number;
}

export function StockChart({ data, period }: Props) {
  // 기간에 따라 X축 레이블 밀도 조정
  const tickCount = period <= 90 ? 6 : period <= 180 ? 6 : 8;
  const step = Math.max(1, Math.floor(data.length / tickCount));
  const ticks = data.filter((_, i) => i % step === 0).map((d) => d.date);

  const minClose = Math.min(...data.map((d) => d.close));
  const maxClose = Math.max(...data.map((d) => d.close));
  const padding = (maxClose - minClose) * 0.05;

  return (
    <ResponsiveContainer width="100%" height={240}>
      <AreaChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
        <defs>
          <linearGradient id="stockGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#3182F6" stopOpacity={0.18} />
            <stop offset="95%" stopColor="#3182F6" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#F2F4F6" vertical={false} />
        <XAxis
          dataKey="date"
          ticks={ticks}
          tickFormatter={formatDate}
          tick={{ fontSize: 11, fill: "#9CA3AF" }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          domain={[minClose - padding, maxClose + padding]}
          tickFormatter={(v: number) => (v / 1000).toFixed(0) + "k"}
          tick={{ fontSize: 11, fill: "#9CA3AF" }}
          axisLine={false}
          tickLine={false}
          width={40}
        />
        <Tooltip
          contentStyle={{
            background: "#fff",
            border: "1px solid #E5E8EB",
            borderRadius: 12,
            fontSize: 12,
          }}
          labelFormatter={(label) => String(label)}
          formatter={(value) => [formatClose(Number(value)), "종가"]}
        />
        <Area
          type="monotone"
          dataKey="close"
          stroke="#3182F6"
          strokeWidth={2}
          fill="url(#stockGradient)"
          dot={false}
          activeDot={{ r: 4, fill: "#3182F6" }}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
