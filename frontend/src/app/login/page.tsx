"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Header } from "@/components/layout/Header";
import { useAuth } from "@/hooks/useAuth";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const {
    isAuthenticated,
    login,
    isLoggingIn,
    loginError,
    register,
    isRegistering,
    registerError,
  } = useAuth();

  useEffect(() => {
    if (isAuthenticated) router.replace("/stocks");
  }, [isAuthenticated, router]);

  const isRegister = mode === "register";
  const pending = isRegister ? isRegistering : isLoggingIn;
  const error = isRegister ? registerError : loginError;

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password || pending) return;
    const args = { email, password };
    if (isRegister) register(args);
    else login(args);
  };

  return (
    <div className="flex flex-col h-screen">
      <Header />
      <main className="flex-1 flex items-center justify-center p-4 bg-[#F9FAFB]">
        <div className="w-full max-w-sm bg-white rounded-2xl p-6 shadow-card border border-border">
          <div className="flex gap-1 bg-[#F2F4F6] rounded-xl p-1 mb-6">
            <button
              type="button"
              onClick={() => setMode("login")}
              className={`flex-1 py-2 text-sm font-semibold rounded-lg transition-colors ${
                !isRegister ? "bg-white text-[#3182F6] shadow-sm" : "text-[#6B7280]"
              }`}
            >
              로그인
            </button>
            <button
              type="button"
              onClick={() => setMode("register")}
              className={`flex-1 py-2 text-sm font-semibold rounded-lg transition-colors ${
                isRegister ? "bg-white text-[#3182F6] shadow-sm" : "text-[#6B7280]"
              }`}
            >
              회원가입
            </button>
          </div>

          <form onSubmit={submit} className="space-y-3">
            <div>
              <label className="text-xs text-[#6B7280] mb-1 block">이메일</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="w-full text-sm border border-border rounded-xl px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-[#3182F6]"
              />
            </div>
            <div>
              <label className="text-xs text-[#6B7280] mb-1 block">비밀번호</label>
              <input
                type="password"
                required
                minLength={isRegister ? 8 : undefined}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder={isRegister ? "8자 이상" : ""}
                className="w-full text-sm border border-border rounded-xl px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-[#3182F6]"
              />
            </div>

            {error && <p className="text-xs text-[#F04452]">{error.message}</p>}

            <button
              type="submit"
              disabled={pending}
              className="w-full py-3 rounded-xl bg-[#3182F6] text-white font-bold disabled:opacity-50"
            >
              {pending ? "처리 중..." : isRegister ? "회원가입" : "로그인"}
            </button>
          </form>

          <p className="text-[11px] text-[#9CA3AF] mt-4 text-center leading-relaxed">
            관심종목·매매일지 저장에만 사용됩니다. 모의투자 자체는 로그인 없이도
            이용할 수 있습니다.
          </p>
        </div>
      </main>
    </div>
  );
}
