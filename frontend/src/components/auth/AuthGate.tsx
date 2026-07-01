"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";

const PUBLIC_PATHS = ["/login"];

// 앱 전체를 로그인 필수로 만드는 게이트. /login 자체는 예외.
export function AuthGate({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuth();
  const isPublic = PUBLIC_PATHS.includes(pathname);

  useEffect(() => {
    if (!isLoading && !isAuthenticated && !isPublic) {
      router.replace("/login");
    }
  }, [isLoading, isAuthenticated, isPublic, router]);

  if (isPublic) return <>{children}</>;

  if (isLoading || !isAuthenticated) {
    return (
      <div className="flex items-center justify-center h-screen bg-[#F9FAFB]">
        <p className="text-sm text-[#9CA3AF]">불러오는 중...</p>
      </div>
    );
  }

  return <>{children}</>;
}
