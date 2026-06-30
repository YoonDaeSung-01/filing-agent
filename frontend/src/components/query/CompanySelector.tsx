"use client";

import { TARGET_COMPANIES } from "@/lib/constants";

interface CompanySelectorProps {
  value: string;
  onChange: (v: string) => void;
}

const INGESTED_SET = new Set<string>(TARGET_COMPANIES);

export function CompanySelector({ value, onChange }: CompanySelectorProps) {
  return (
    <div className="space-y-1.5">
      <label className="text-xs font-semibold text-[#6B7280] uppercase tracking-wider">
        기업
      </label>
      <div className="relative">
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="기업명 입력 또는 선택"
          list="company-list"
          className="w-full px-3 py-2 text-sm border border-border rounded-xl bg-white text-[#191F28] placeholder:text-[#6B7280] focus:outline-none focus:ring-2 focus:ring-[#3182F6] focus:border-transparent transition-all"
        />
        <datalist id="company-list">
          {TARGET_COMPANIES.map((c) => (
            <option key={c} value={c} />
          ))}
        </datalist>
      </div>
      {value && !INGESTED_SET.has(value) && (
        <p className="text-xs text-[#6B7280]">
          💡 수치 조회 가능 · 본문 검색은 인제스트 후 지원
        </p>
      )}
    </div>
  );
}
