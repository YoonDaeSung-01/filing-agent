export function Header() {
  return (
    <header className="border-b border-border bg-white px-6 py-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-[#191F28] tracking-tight">
            DART Filing Agent
          </h1>
          <p className="text-sm text-[#6B7280] mt-0.5">
            공시 데이터 기반 재무 Q&A
          </p>
        </div>
        <span className="text-xs text-[#6B7280] bg-[#F2F4F6] px-3 py-1.5 rounded-full">
          ⓘ 투자 조언 아님 · 공시 사실 추출
        </span>
      </div>
    </header>
  );
}
