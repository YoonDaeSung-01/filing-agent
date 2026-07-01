"use client";

import Link from "next/link";
import { Star } from "lucide-react";
import { Header } from "@/components/layout/Header";
import { WatchlistRow } from "@/components/stock/WatchlistRow";
import { useAuth } from "@/hooks/useAuth";
import { useWatchlist } from "@/hooks/useWatchlist";

export default function WatchlistPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { items, remove } = useWatchlist();

  return (
    <div className="flex flex-col h-screen">
      <Header />
      <main className="flex-1 overflow-y-auto p-4 md:p-6 bg-[#F9FAFB]">
        <div className="max-w-2xl mx-auto space-y-4">
          <div>
            <h2 className="text-lg font-bold text-[#191F28]">관심종목</h2>
            <p className="text-xs text-[#6B7280] mt-0.5">
              저장한 종목의 현재가를 한눈에 확인하고, 눌러서 상세로 이동하세요.
            </p>
          </div>

          {!authLoading && !isAuthenticated && (
            <div className="bg-white rounded-2xl p-8 text-center border border-border shadow-card">
              <Star size={28} className="mx-auto text-[#D1D5DB] mb-3" />
              <p className="text-sm text-[#191F28] font-semibold mb-1">
                로그인하고 관심종목을 저장해보세요
              </p>
              <p className="text-xs text-[#9CA3AF] mb-4">
                주가 화면의 별 아이콘으로 종목을 추가하면 여기 모아볼 수 있어요.
              </p>
              <Link
                href="/login"
                className="inline-block text-sm font-semibold text-white bg-[#3182F6] px-5 py-2.5 rounded-xl"
              >
                로그인 / 회원가입
              </Link>
            </div>
          )}

          {isAuthenticated && items.length === 0 && (
            <div className="bg-white rounded-2xl p-8 text-center border border-border shadow-card">
              <Star size={28} className="mx-auto text-[#D1D5DB] mb-3" />
              <p className="text-sm text-[#191F28] font-semibold mb-1">
                아직 관심종목이 없어요
              </p>
              <p className="text-xs text-[#9CA3AF] mb-4">
                주가 화면에서 종목을 검색하고 별 아이콘을 눌러 추가해보세요.
              </p>
              <Link
                href="/stocks"
                className="inline-block text-sm font-semibold text-white bg-[#3182F6] px-5 py-2.5 rounded-xl"
              >
                종목 둘러보기
              </Link>
            </div>
          )}

          {isAuthenticated && items.length > 0 && (
            <div className="space-y-2">
              {items.map((item) => (
                <WatchlistRow
                  key={item.name}
                  company={item.name}
                  onRemove={() => remove(item.name)}
                />
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
