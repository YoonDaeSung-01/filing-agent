"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const TABS = [
  { href: "/", label: "재무 Q&A" },
  { href: "/stocks", label: "주가" },
];

export function Header() {
  const pathname = usePathname();

  return (
    <header className="border-b border-border bg-white px-6 py-0">
      <div className="flex items-center justify-between pt-4 pb-0">
        <div>
          <h1 className="text-xl font-bold text-[#191F28] tracking-tight">
            DART Filing Agent
          </h1>
          <p className="text-sm text-[#6B7280] mt-0.5">
            공시 데이터 기반 재무 분석
          </p>
        </div>
        <span className="text-xs text-[#6B7280] bg-[#F2F4F6] px-3 py-1.5 rounded-full">
          ⓘ 투자 조언 아님 · 공시 사실 추출
        </span>
      </div>

      {/* 탭 */}
      <nav className="flex gap-0 mt-3">
        {TABS.map((tab) => {
          const active = pathname === tab.href;
          return (
            <Link
              key={tab.href}
              href={tab.href}
              className={[
                "px-4 py-2.5 text-sm font-semibold border-b-2 transition-colors",
                active
                  ? "border-[#3182F6] text-[#3182F6]"
                  : "border-transparent text-[#6B7280] hover:text-[#191F28]",
              ].join(" ")}
            >
              {tab.label}
            </Link>
          );
        })}
      </nav>
    </header>
  );
}
