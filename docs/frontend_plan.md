# filing-agent 프론트엔드 설계 계획 (v2 — 코드 검증 반영)

## 개요

DART 공시 기반 재무 Q&A 에이전트의 웹 인터페이스.
단순 챗 UI가 아니라 **에이전트 내부(도구 라우팅·하네스 검증·결정론 수치·출처)를 시각적으로 드러내는**
포트폴리오용 데모. "RAG 챗봇"이 아니라 "검증되는 도구 에이전트"임을 화면으로 증명하는 게 목표다.

디자인 기조: **토스(Toss) 스타일** — 여백 충분·타이포그래피 중심·카드 기반·불필요한 장식 없음.

---

## 검증 결과 (v1 → v2 변경 사유)

실제 백엔드 코드(`agent/graph.py`·`agent/tools.py`·`api/main.py`·`harness/*`)를 읽고 v1 계획을
검증한 결과 **치명적 결함 1건 + 보강 3건**을 발견해 반영했다.

### 🔴 결함 (plan-breaking) — 재무 카드의 데이터 출처가 틀렸다

v1은 `FinancialCard`/`ChangeCard`/`SumCard`를 `tool_log`에서 뽑겠다고 했으나, 실제 `tool_log`는
도구 **이름·입력 인자·성공여부**만 담는다(`graph.py:132`):

```python
tool_log.append({"tool": name, "args": args, "ok": ok})
```

반환값(`value`·`delta`·`pct_change`·`total`·`fs_div`)은 `state["facts"]`에 구조화되어 쌓이지만
(`graph.py:139`), **API 응답(`AskResponse`)은 `answer`/`sources`/`tool_log`만 반환하고 `facts`를
내보내지 않는다**(`main.py:136-140`).

→ **해결: `AskResponse`에 `facts` 추가(백엔드 2줄 변경).** 답변 텍스트에서 숫자를 파싱하는 대안은
프로젝트 핵심 원칙("LLM이 숫자를 텍스트에서 옮기지 않게 한다")을 위반하므로 채택하지 않는다.
`facts`는 verifier가 이미 신뢰하는 결정론 값이라, 이를 그대로 노출하는 게 정합적이다.

### 🟡 보강 1 — 가드레일 차단 상태를 별도 UI로

입력 가드(`guardrails.check_input`)가 프롬프트 인젝션/투자조언을 차단하면, 그래프는 `input_guard`에서
바로 END로 가서 `{answer: <거부 메시지>, sources: [], tool_log: []}`를 반환한다(`graph.py:71-76`).
이건 "정상 답변 없음"이 아니라 **안전 계층이 작동한 상태**다. 별도 배지로 표시하면 하네스(가드레일)를
보여주는 강력한 데모가 된다. v1엔 이 상태 처리가 없었다 → `GuardrailNotice` 컴포넌트 추가.

### 🟡 보강 2 — 타임라인 타이밍 데이터 없음

v1 타임라인은 "✓ 0.3s"를 그렸지만 `tool_log`에 소요시간이 없다. **선택적으로** `_node_call_tools`에서
도구별 실행시간(`ms`)을 측정해 `tool_log`에 추가한다(없으면 타임라인에서 시간만 숨김). 필수 아님.

### 🟡 보강 3 — 카드 구분자(discriminator)를 모양 기반으로 명시

`facts` 항목은 도구 이름 태그가 없지만 **모양으로 구분 가능**하며, 이는 백엔드 `_summarize_facts`
(`graph.py:262-277`)와 정확히 동일한 판정이다:

| 도구 | 식별 키 | 카드 |
|---|---|---|
| `compute_sum` | `total` + `values` 존재 | SumCard |
| `compute_change` | `delta` 존재 | ChangeCard |
| `financial_lookup` | `value` 존재(`delta`·`total` 없음) | FinancialCard |

`facts`에는 `found:False`(실패) 항목이 들어오지 않는다(`graph.py:134-139`에서 성공만 적재) →
프론트에서 별도 필터 불필요.

---

## 백엔드 선행 변경 (프론트 전제조건)

프론트 구현 전에 백엔드를 먼저 고친다. 모두 작고 기존 테스트와 충돌하지 않는 가산적 변경이다.

### ① `AskResponse`에 `facts` 추가 — 필수 (`api/main.py`)

```python
class AskResponse(BaseModel):
    answer: str
    sources: list[str]
    tool_log: list[dict] = []
    facts: list[dict] = []          # ← 추가: 카드 렌더용 구조화 수치

@app.post("/ask")
def ask_agent(request: AskRequest) -> AskResponse:
    ...
    return AskResponse(
        answer=final.get("answer") or "",
        sources=final.get("sources") or [],
        tool_log=final.get("tool_log") or [],
        facts=final.get("facts") or [],   # ← 추가
    )
```

### ② CORS 미들웨어 — 필수 (`api/main.py`)

Next.js dev 서버(`localhost:3000`)에서 FastAPI(`localhost:8000`)를 호출하려면 필요.

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
```

### ③ 도구별 실행시간 측정 — 선택 (`agent/graph.py`)

```python
import time
...
t0 = time.perf_counter()
result, ok = fn.invoke(args), True
...
tool_log.append({"tool": name, "args": args, "ok": ok,
                 "ms": round((time.perf_counter() - t0) * 1000)})
```

---

## 백엔드 API 계약 (검증 완료 — 실제 코드 기준)

```ts
// POST /ask  요청
interface AskRequest {
  question: string;
  company?: string | null;   // 선택 — 라우팅 힌트
  year?: number | null;      // 선택 — 라우팅 힌트
}

// POST /ask  응답 (facts·status 추가 후)
interface AskResponse {
  answer: string;            // 사용자에게 보일 산문 답변
  sources: string[];         // 출처 문자열(중복 제거됨). compute_sum 도 평탄화되어 들어옴
  tool_log: ToolLogEntry[];  // 도구 선택 과정(라우팅 투명성)
  facts: Fact[];             // 카드 렌더용 결정론 수치(성공 결과만)
  status: "ok" | "blocked" | "failed";  // 프론트 상태 분기(결정론) — 문자열 매칭 불필요
}

interface ToolLogEntry {
  tool: "doc_search" | "financial_lookup" | "compute_change" | "compute_sum";
  args: Record<string, unknown>;
  ok: boolean;
  ms?: number;               // 선택(보강 3 적용 시)
}

// facts 는 모양으로 구분되는 판별 유니온
type Fact = LookupFact | ChangeFact | SumFact;

interface LookupFact {       // financial_lookup
  company: string; account: string; year: number;
  value: number; fs_div: "CFS" | "OFS"; source: string;
}
interface ChangeFact {       // compute_change ("delta" 보유)
  company: string; account: string;
  year_from: number; value_from: number;
  year_to: number;   value_to: number;
  delta: number; pct_change: number | null;
  fs_div: string; source: string;
}
interface SumFact {          // compute_sum ("total" + "values" 보유)
  companies: string[]; account: string; year: number;
  values: { company: string; value: number }[];
  total: number; fs_div: "CFS" | "OFS" | "MIXED"; source: string[];
}

function factKind(f: Fact): "lookup" | "change" | "sum" {
  if ("total" in f && "values" in f) return "sum";
  if ("delta" in f) return "change";
  return "lookup";
}
```

**상태 분기는 `status` 필드로 결정론 처리한다**(거부 메시지 문자열 매칭 같은 휴리스틱 불필요):
`"blocked"`=가드레일 차단(인젝션·투자조언 선회), `"failed"`=우아한 실패(검증/예산 소진),
`"ok"`=정상. 백엔드 `graceful_fail`·`input_guard`가 이 값을 세팅해 응답에 그대로 실린다.

---

## 기술 스택

| 분야 | 선택 | 이유 |
|---|---|---|
| 프레임워크 | Next.js 15 (App Router) | 파일 기반 라우팅, TypeScript 1급 지원, 빌드 성숙도 |
| 언어 | TypeScript | 위 API 계약을 타입으로 고정 |
| 스타일링 | Tailwind CSS v4 | Next.js가 스타일 솔루션을 안 갖고 있어 별도 선택 필요. Toss 토큰화 용이 |
| UI 프리미티브 | shadcn/ui | Accordion·Select·Skeleton 등 접근성 갖춘 컴포넌트 |
| 데이터 패칭 | TanStack Query | 로딩·에러·캐싱 일관 처리(뮤테이션) |
| 애니메이션 | Framer Motion | 카드 진입·타임라인 stagger |
| 폰트 | Pretendard | 한국어 최적화(Toss 실사용 폰트) |
| 패키지 관리 | npm | Next.js 생태계 기본 |

> Tailwind는 프레임워크(Next.js)와 별개 레이어(CSS 유틸리티)다. Next.js 자체엔 스타일링 솔루션이
> 없어 CSS Modules / CSS-in-JS / Tailwind 중 택해야 하며, `create-next-app` 공식 옵션이자 사실상 표준.

---

## 기존 백엔드 기능 → UI 매핑 (v2 — facts 기반으로 수정)

| 백엔드 산출물 | 소스 필드 | 프론트 UI | 표현 |
|---|---|---|---|
| 산문 답변 | `answer` | AnswerCard | 본문 텍스트, fade-in |
| 재무 수치 | **`facts`** (LookupFact) | FinancialCard | 큰 숫자 타이포, 조·억 변환, CFS/OFS 배지 |
| 증감 계산 | **`facts`** (ChangeFact) | ChangeCard | ▲/▼ + 증감액 + 증감률%, 전기·당기 |
| 다기업 합산 | **`facts`** (SumFact) | SumCard | 기업별 분해 + 합계 강조 |
| 도구 선택 과정 | `tool_log` | ToolTimeline | 실행 순서·성공여부(✓/✗)·인자 요약·(선택)ms |
| 출처 | `sources` | SourcePanel | 접이식 출처 목록 |
| 가드레일 차단 | `answer`+빈 로그 | GuardrailNotice | 인젝션/투자조언 선회 배지 + 안내문 |
| graceful_fail | `answer`(확인된 부분) | AnswerCard(경고 톤) | 부분 확인 + 재질문 유도 |
| 지원 계정 8개 | 프론트 상수 | QuickQueries | 원클릭 질문 생성 칩 |
| 기본 기업 10개 | 프론트 상수 | CompanySelector | 드롭다운 + 직접 입력(임의 기업 허용) |

> **중요(정직한 스코프 표기):** `financial_lookup`은 DART 등록 **모든 상장사**에 동작하고(카카오 포함),
> `doc_search`는 pgvector 인제스트된 기업(기본 10개)만 동작한다. CompanySelector는 임의 입력을 허용하되,
> 목록 밖 기업엔 "수치는 조회 가능 · 본문 검색은 인제스트 후 가능" 힌트를 보인다.

---

## 디렉터리 구조

```
frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx          # Pretendard, 전역 레이아웃
│   │   ├── page.tsx            # 메인 Q&A 페이지
│   │   ├── globals.css         # Tailwind 베이스 + Toss 토큰
│   │   └── providers.tsx       # QueryClientProvider
│   │
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Header.tsx          # 로고 + 태그라인 + 투자조언 아님 고지
│   │   │   └── Sidebar.tsx         # 히스토리 패널
│   │   ├── query/
│   │   │   ├── QueryForm.tsx       # 질문 입력 + 제출
│   │   │   ├── CompanySelector.tsx # 드롭다운 + 직접 입력 + 스코프 힌트
│   │   │   ├── YearSelector.tsx    # Segmented control
│   │   │   └── QuickQueries.tsx    # 빠른 질문 칩
│   │   ├── result/
│   │   │   ├── ResultPanel.tsx     # 결과 컨테이너(상태 분기)
│   │   │   ├── AnswerCard.tsx      # 산문 답변
│   │   │   ├── FinancialCard.tsx   # LookupFact
│   │   │   ├── ChangeCard.tsx      # ChangeFact
│   │   │   ├── SumCard.tsx         # SumFact
│   │   │   ├── FactCards.tsx       # facts[] → factKind() 분기 렌더
│   │   │   ├── ToolTimeline.tsx    # tool_log 타임라인
│   │   │   ├── GuardrailNotice.tsx # 가드레일 차단 상태
│   │   │   └── SourcePanel.tsx     # 출처 Accordion
│   │   └── ui/                     # shadcn/ui 생성물
│   │
│   ├── hooks/
│   │   ├── useAsk.ts           # POST /ask 뮤테이션
│   │   └── useQueryHistory.ts  # sessionStorage 히스토리
│   │
│   └── lib/
│       ├── api.ts              # fetch 클라이언트
│       ├── types.ts            # 위 API 계약 타입 + factKind()
│       ├── format.ts           # 원→"300.9조" 변환
│       ├── guardrail.ts        # 차단 응답 판별 헬퍼
│       └── constants.ts        # 기업10·계정8·연도
│
├── next.config.ts              # rewrites: /api/* → :8000 (선택)
├── tailwind.config.ts          # Toss 팔레트 + Pretendard
└── .env.local                  # NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 화면 설계 (메인 `/`)

```
┌─────────────────────────────────────────────────────────────────┐
│  DART Filing Agent              ⓘ 투자 조언 아님 · 공시 사실 추출  │
├────────────────────────┬────────────────────────────────────────┤
│  기업 [삼성전자 ▼]     │  ┌─ 빠른 질문 ─────────────────────┐  │
│  연도 [2023][2024]     │  │ [매출액][영업이익][자본총계]…    │  │
│                        │  │ [전년대비 증감][사업 전략][합산] │  │
│  ── 히스토리 ──        │  └──────────────────────────────────┘  │
│  · 삼성 매출액         │  ┌─ 질문 입력 ─────────────────────┐  │
│  · SK 위험요인         │  │ 삼성전자의 2024년 매출액은?       │  │
│  · 두 기업 합산        │  │                    [질의하기 →]   │  │
│                        │  └──────────────────────────────────┘  │
│                        │  ┌─ 결과 ──────────────────────────┐  │
│                        │  │ ToolTimeline                     │  │
│                        │  │  ● financial_lookup  ✓           │  │
│                        │  │ FactCards → FinancialCard        │  │
│                        │  │ AnswerCard(산문)                 │  │
│                        │  │ ▶ 출처 보기 (N건)                │  │
│                        │  └──────────────────────────────────┘  │
└────────────────────────┴────────────────────────────────────────┘
```

### 결과 상태 분기 (ResultPanel)

```
응답 도착 → switch (status)
  ├ "blocked" → GuardrailNotice (인젝션/투자조언 선회 — 안전 계층 배지)
  ├ "failed"  → AnswerCard(주의 톤, 빨강 아님) + (있으면)부분 출처
  └ "ok" →
       ├ facts.length > 0 → ToolTimeline + FactCards(분기) + AnswerCard + SourcePanel
       └ facts.length == 0 → ToolTimeline + AnswerCard + SourcePanel (순수 doc_search)
```

### 카드 상세

**FinancialCard** (LookupFact)
```
┌──────────────────────────────┐
│ 매출액                  2024 │
│ 300.9조 원                   │
│ 300,870,903,000,000          │
│ 연결(CFS) · OpenDART          │
└──────────────────────────────┘
```

**ChangeCard** (ChangeFact)
```
┌──────────────────────────────┐
│ 매출액 증감   2023 → 2024    │
│ ▲ 41.9조   +16.2%            │
│ 전기 258.9조 / 당기 300.9조  │
└──────────────────────────────┘
```
pct_change 가 null 이면(전기=0) "%—"로 표기.

**SumCard** (SumFact)
```
┌──────────────────────────────┐
│ 매출액 합산           2024   │
│ 삼성전자      300.9조        │
│ SK하이닉스     66.2조        │
│ ───────────────────          │
│ 합계         367.1조  (MIXED?)│
└──────────────────────────────┘
```
fs_div 가 "MIXED"면 "연결/별도 혼합" 주석.

---

## UI/UX 보강 (간단 — 데모 설득력 위주)

큰 기능 추가 없이, 작은 디테일로 "신뢰감·이해도"를 올리는 것만 추린다.

1. **빈 상태 온보딩** — 결과 전 화면에 예시 질문 3개를 카드로(매출액·증감·합산). 무엇을 물어볼 수 있는지
   즉시 전달 → 첫 클릭까지의 마찰 제거. (QuickQueries 재사용)
2. **출처를 답변 옆 인라인 칩으로** — 제품 정체성이 "출처와 함께"이므로 Accordion에 숨기지 말고
   AnswerCard 하단에 `[출처 1] [출처 2]` 칩을 바로 노출(상세는 SourcePanel에서 펼침).
3. **숫자 복사 버튼** — FinancialCard의 원 단위 정수를 한 번에 복사(실무 사용성). 클릭 시 토스트.
4. **graceful_fail는 에러색이 아니라 주의색** — `failed`는 빨강이 아닌 노랑/회색 톤. "부분 정보는 유효,
   질문을 좁히면 됨"을 색으로 전달(좌절감 ↓).
5. **로딩은 정직하게** — 가짜 단계 진행바 대신 결과 영역 Skeleton 1개. (진짜 단계 표시는 스트리밍 필요 →
   범위 밖, 아래 백엔드 확장 참고)
6. **색 외 신호 병행** — 증감은 색(빨강/파랑)만이 아니라 ▲/▼ 화살표를 항상 병기(색각 접근성).

## 백엔드 확장 고려 (적용 1 + 보류 3)

| 항목 | 판단 | 비고 |
|---|---|---|
| `status` 필드 노출 | ✅ **적용함** | 프론트 상태 분기를 문자열 매칭 휴리스틱 → 결정론 필드로. `graceful_fail`에 status 세팅 + `AskResponse.status`. 테스트 통과. |
| `GET /meta`(기업·계정·연도 목록) | 🔸 선택 | 프론트가 `constants.ts`에 8계정·10기업을 하드코딩하면 백엔드와 드리프트. 메타 엔드포인트로 단일 출처화 가능. 지금은 하드코딩으로 시작, 필요 시 추가. |
| `tool_log[].ms`(도구 소요시간) | 🔸 선택 | 타임라인에 시간 표시용. `_node_call_tools`에서 측정. 데모 디테일, 필수 아님. |
| SSE 스트리밍(도구 실행 라이브 표시) | ⏸ 보류 | 타임라인을 실시간으로 채우면 임팩트 크지만 LangGraph 스트리밍 + EventSource로 복잡도 급증. "간단" 원칙상 v1 범위 밖. |

## Toss 디자인 토큰

```ts
colors: {
  toss: {
    blue: '#3182F6', blueDim: '#EBF3FF',
    up: '#F04452',   down: '#1677FF',   // 증가=빨강/감소=파랑(국내 관례)
    gray50: '#F9FAFB', gray100: '#F2F4F6', gray300: '#D1D5DB',
    gray600: '#6B7280', gray900: '#191F28',
  }
}
borderRadius: { card: '16px', chip: '8px', input: '12px' }
boxShadow:    { card: '0 2px 8px rgba(0,0,0,0.06)' }
```

---

## 숫자 포맷 (`lib/format.ts`)

```ts
export function formatKRW(value: number): string {
  const abs = Math.abs(value);
  if (abs >= 1_0000_0000_0000) return `${(value / 1_0000_0000_0000).toFixed(1)}조`;
  if (abs >= 1_0000_0000)      return `${Math.round(value / 1_0000_0000)}억`;
  return value.toLocaleString('ko-KR');
}
export function formatPct(pct: number | null): string {
  if (pct === null) return '—';
  return `${pct >= 0 ? '+' : ''}${pct}%`;
}
```

---

## 구현 순서

### Phase 0 — 백엔드 선행 + 프로젝트 세팅 (40분)
- **백엔드:** `AskResponse.facts` 추가 + CORS 미들웨어 → `ruff check` · `pytest` 통과 확인 → 커밋
- `npx create-next-app@latest frontend --typescript --tailwind --app --src-dir`
- shadcn/ui 초기화, Pretendard, Toss 토큰 등록
- `lib/types.ts`(API 계약) · `api.ts` · `format.ts` · `guardrail.ts` · `constants.ts`

### Phase 1 — 기본 Q&A + 투명성 (45분)
- `QueryForm` + `useAsk`(뮤테이션, 로딩·에러)
- `AnswerCard` + Skeleton
- `ToolTimeline`(tool_log) — 라우팅 투명성, 데모 임팩트 최상
- `GuardrailNotice` — 투자조언/인젝션 차단 표시(하네스 데모)

### Phase 2 — 재무 카드(facts 기반) + 빠른 질문 (50분)
- `FactCards` — `factKind()`로 분기
- `FinancialCard` / `ChangeCard` / `SumCard`
- `QuickQueries` — 계정 8개 + 증감·전략·합산 프리셋

### Phase 3 — 회사/연도 + 출처 + 히스토리 (35분)
- `CompanySelector`(드롭다운+직접입력+스코프 힌트) · `YearSelector`
- `SourcePanel`(Accordion) · `useQueryHistory`(sessionStorage)

### Phase 4 — 마무리 (30분)
- Framer Motion 진입/ stagger
- 모바일 반응형(Sidebar → 상단 접이)
- graceful_fail 경고 톤 분기
- `README` 프론트 섹션 + 실행법

---

## 완성 검증 체크리스트

- [ ] (백엔드) `AskResponse.facts` 노출 + 기존 pytest 통과
- [ ] (백엔드) CORS 로 `localhost:3000` 호출 성공
- [ ] financial_lookup → FinancialCard(조·억·CFS/OFS)
- [ ] compute_change → ChangeCard(▲/▼·%·null pct 처리)
- [ ] compute_sum → SumCard(분해·합계·MIXED)
- [ ] doc_search 단독 → AnswerCard + SourcePanel(facts 없음)
- [ ] 하이브리드(facts+doc) → 카드 + 산문 + 출처 동시
- [ ] 투자조언 질문 → GuardrailNotice(선회 안내)
- [ ] 프롬프트 인젝션 → GuardrailNotice(차단)
- [ ] graceful_fail → 경고 톤 + 부분 확인
- [ ] 빠른 질문 → 폼 자동완성, 히스토리 재실행
- [ ] 모바일(375px) 레이아웃 유지
```
