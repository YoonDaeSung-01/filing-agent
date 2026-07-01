"use client";

import { Newspaper, ExternalLink } from "lucide-react";
import { useNews } from "@/hooks/useNews";

function timeAgo(pubDate: string): string {
  const d = new Date(pubDate);
  if (isNaN(d.getTime())) return "";
  const diffMin = Math.floor((Date.now() - d.getTime()) / 60000);
  if (diffMin < 60) return `${Math.max(diffMin, 0)}분 전`;
  const diffHour = Math.floor(diffMin / 60);
  if (diffHour < 24) return `${diffHour}시간 전`;
  return `${Math.floor(diffHour / 24)}일 전`;
}

export function NewsPanel({ company }: { company: string }) {
  const { data, isLoading, error } = useNews(company);

  return (
    <div className="bg-white rounded-2xl p-5 shadow-card border border-border">
      <div className="flex items-center gap-2 mb-3">
        <Newspaper size={15} className="text-[#6B7280]" />
        <p className="text-sm font-bold text-[#191F28]">관련 뉴스</p>
        <span className="text-xs text-[#9CA3AF]">사실 요약 · 투자 조언 아님</span>
      </div>

      {isLoading && (
        <div className="space-y-2">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-14 bg-[#F2F4F6] rounded-xl animate-pulse" />
          ))}
        </div>
      )}

      {error && !isLoading && (
        <p className="text-xs text-[#92400E]">뉴스를 불러올 수 없습니다: {error.message}</p>
      )}

      {data && !data.found && <p className="text-xs text-[#92400E]">{data.reason}</p>}

      {data && data.found && data.items.length === 0 && (
        <p className="text-xs text-[#9CA3AF] text-center py-4">관련 뉴스가 없습니다.</p>
      )}

      {data && data.found && data.items.length > 0 && (
        <ul className="space-y-1.5">
          {data.items.map((item, i) => (
            <li key={i}>
              <a
                href={item.link}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-start justify-between gap-2 px-3 py-2.5 rounded-xl hover:bg-[#F9FAFB] transition-colors group"
              >
                <div className="min-w-0">
                  <p className="text-sm text-[#191F28] leading-snug line-clamp-2 group-hover:text-[#3182F6]">
                    {item.title}
                  </p>
                  <p className="text-xs text-[#9CA3AF] mt-1">
                    {item.source} · {timeAgo(item.pub_date)}
                  </p>
                </div>
                <ExternalLink size={13} className="text-[#D1D5DB] shrink-0 mt-1" />
              </a>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
