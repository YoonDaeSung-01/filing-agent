// 백엔드 constants.py / tools.py 와 동기화
// 변경 시 양쪽 모두 업데이트 필요

export const TARGET_COMPANIES = [
  "삼성전자",
  "SK하이닉스",
  "LG전자",
  "현대자동차",
  "기아",
  "POSCO홀딩스",
  "LG화학",
  "삼성SDI",
  "현대모비스",
  "SK이노베이션",
] as const;

export const CANONICAL_ACCOUNTS = [
  "매출액",
  "영업이익",
  "법인세차감전순이익",
  "당기순이익",
  "총포괄손익",
  "자산총계",
  "부채총계",
  "자본총계",
] as const;

export const TARGET_YEARS = [2022, 2023, 2024] as const;

// 빠른 질문 프리셋 — QuickQueries 컴포넌트에서 사용
export interface QuickQuery {
  label: string;
  questionFn: (company: string, year: number) => string;
  category: "lookup" | "change" | "doc" | "combine";
}

export const QUICK_QUERIES: QuickQuery[] = [
  {
    label: "매출액",
    questionFn: (c, y) => `${c} ${y}년 매출액은?`,
    category: "lookup",
  },
  {
    label: "영업이익",
    questionFn: (c, y) => `${c} ${y}년 영업이익은?`,
    category: "lookup",
  },
  {
    label: "당기순이익",
    questionFn: (c, y) => `${c} ${y}년 당기순이익은?`,
    category: "lookup",
  },
  {
    label: "자산총계",
    questionFn: (c, y) => `${c} ${y}년 자산총계는?`,
    category: "lookup",
  },
  {
    label: "전년 대비 증감",
    questionFn: (c, y) => `${c}의 ${y - 1}년 대비 ${y}년 매출액 증감은?`,
    category: "change",
  },
  {
    label: "사업 전략",
    questionFn: (c, y) => `${c} ${y}년 사업보고서에서 주요 사업 전략을 설명해줘`,
    category: "doc",
  },
  {
    label: "위험 요인",
    questionFn: (c, y) => `${c}가 ${y}년 사업보고서에서 밝힌 주요 위험 요인은?`,
    category: "doc",
  },
];

export const TOOL_LABELS: Record<string, string> = {
  financial_lookup: "재무 조회",
  compute_change: "증감 계산",
  compute_sum: "합산",
  doc_search: "문서 검색",
};
