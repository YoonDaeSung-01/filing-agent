# Phase 3 설계서 — 에이전트화 + 도구 라우팅 (LangGraph)

> 작성일: 2026-06-26 · 상태: **설계 확정 대기(구현 전)**
> 근거: `docs/plan.md` Phase 3. 이 문서는 "만들 파일·State 스키마·노드 구성"을 먼저 합의하기 위한 것.

## 1. 목표 & 범위

**목표** — 답을 바로 만들지 않고, 질문에 맞는 **도구를 에이전트가 고르고**, 하이브리드 질문이면 여러 도구를 모아 종합한다.

| 들어가는 것 (Phase 3) | 빠지는 것 (Phase 4로) |
|---|---|
| 도구 3종(doc_search / financial_lookup / compute_change) | 검증 루프(verifier) — 자리만 남김 |
| 표준계정 정규화 + CFS/OFS 처리 | 가드레일(인젝션 차단·투자조언 선회) |
| LangGraph ReAct 그래프 + max_steps/예산 | LLM-judge·평가셋(Phase 5) |
| POST /ask 를 에이전트 경유로 교체 | 우아한 실패는 **최소 버전만**(부분결과 안내) |

> 원칙(CLAUDE.md): 숫자는 도구가 **타입 있는 구조화 값**으로 반환 → LLM이 숫자를 손으로 옮기지 않게.

---

## 2. 만들 / 수정할 파일

| 파일 | 신규/수정 | 역할 |
|---|---|---|
| `agent/__init__.py` | 신규 | 패키지 |
| `agent/tools.py` | 신규 | 도구 3종 정의(구조화 반환) + 표준계정 정규화 |
| `agent/state.py` | 신규 | `AgentState` 스키마 + 루프 예산 상수 |
| `agent/graph.py` | 신규 | LangGraph 그래프(노드/엣지/종료조건) |
| `ingest/facts.py` | 수정 | `compute_change` 가 쓸 `extract_change` 순수 함수 추가(전기/당기) |
| `api/main.py` | 수정 | `POST /ask` 를 `agent.graph` 호출로 교체(기존 RAG는 fallback/제거) |
| `config.py` | 수정 | `agent_max_steps`, `agent_budget_tokens` 추가 |
| `tests/test_tools.py` | 신규 | 도구 순수 로직 테스트(픽스처, 키·네트워크 불필요) |
| `tests/test_graph.py` | 신규 | 그래프 라우팅 테스트(가짜 LLM/도구 주입) |
| `pyproject.toml` | 수정 | `langgraph`, `langchain-litellm`(또는 직접 litellm 노드) 추가 |

> 데이터는 이미 준비됨: `data/raw/facts/{corp_code}_{year}_{reprt_code}.json`(원본 DART 페이로드 캐시),
> 각 행에 `thstrm_amount`(당기)·`frmtrm_amount`(전기)가 함께 있어 **2024 보고서 1개로 2023→2024 증감 계산 가능**.

---

## 3. 도구 3종 (agent/tools.py)

도구 설명(description)이 곧 에이전트 사용설명서다 — 명확히 쓴다.

### 3.1 doc_search — 공시 서술 의미 검색
```python
def doc_search(query: str, company: str | None = None, year: int | None = None) -> list[dict]:
    """공시 '서술' 내용(사업 위험·전략·경영진단 등)을 의미 검색한다.
    수치(매출/이익 등)는 financial_lookup 을 쓸 것. 반환: [{content, source}, ...]."""
```
- Phase 1~2의 `retrieval.retriever.search()` 를 그대로 래핑(하이브리드+리랭킹 포함).

### 3.2 financial_lookup — 재무 수치 구조화 조회
```python
def financial_lookup(company: str, account: str, year: int) -> dict:
    """공시된 재무 '수치'를 타입 있는 값으로 반환한다.
    account ∈ {매출액, 영업이익, 당기순이익, 자산총계, 부채총계}.
    반환: {company, account, year, value(원), fs_div, source} | {found: False, reason}."""
```
- 흐름: company → corp_code(캐시된 corpCode.xml) → `facts/{corp_code}_{year}_11011.json` 로드
  → **표준계정 정규화**로 account 매칭 → `build_revenue_fact`(CFS 우선, 없으면 OFS 폴백).
- 못 찾으면 예외 던지지 말고 `{found: False, reason}` 반환(에이전트가 우아하게 처리).

### 3.3 compute_change — 증감 계산(도구 내부)
```python
def compute_change(company: str, account: str, year_from: int, year_to: int) -> dict:
    """두 연도 사이 증감액·증감률을 도구 내부에서 계산해 반환한다(LLM은 식별자만 전달).
    반환: {company, account, year_from, value_from, year_to, value_to,
           delta(원), pct_change(%), fs_div, source} | {found: False, reason}."""
```
- `year_to == year_from+1` 이고 `year_to == TARGET_YEAR(2024)` 면 **단일 파일**의 당기/전기로 계산.
  그 외 연도쌍은 두 파일을 로드(현재 캐시 범위 밖이면 `found: False`).
- `pct_change = (value_to - value_from) / |value_from| * 100`, 0 분모 방어.

### 3.4 표준계정 정규화 (account normalization)
회사·업종마다 계정명이 다르다 → 표준 5개로 흡수하는 동의어 맵.
```python
ACCOUNT_SYNONYMS = {
  "매출액": {"매출액", "수익(매출액)", "영업수익", "매출"},
  "영업이익": {"영업이익", "영업이익(손실)"},
  "당기순이익": {"당기순이익", "당기순이익(손실)", "분기순이익"},
  "자산총계": {"자산총계"},
  "부채총계": {"부채총계"},
}
```
- `extract_account` 매칭 시 `account_nm in synonyms[canonical]` 로 비교(기존 정확일치 대체).
- ⚠️ 당기순이익은 주요계정 API 에서 종목별로 누락될 수 있음 → `found: False, reason="주요계정 미제공"`.

---

## 4. State 스키마 (agent/state.py)

```python
class AgentState(TypedDict):
    question: str
    company: str | None          # 선택 필터(요청에서 옴)
    year: int | None
    messages: Annotated[list, add_messages]   # LLM·tool 메시지 누적(LangGraph 리듀서)
    tool_log: list[dict]         # [{tool, args, ok}] — 관측/검증/평가용
    steps: int                   # 누적 도구 호출 스텝(예산 카운터)
    answer: str | None
    sources: list[str]

AGENT_MAX_STEPS = 6              # config 로 외부화
AGENT_BUDGET_TOKENS = 8000      # (Phase 4 에서 실제 강제)
```

---

## 5. LangGraph 그래프 (agent/graph.py)

ReAct 순환: **추론(LLM) → 도구 → 관찰 → 다시 추론**, 종료조건/예산 포함.

```
        ┌─────────────┐
   ▶───▶│  call_model │  (LLM: 도구 호출 or 최종답변 결정)
        └──────┬──────┘
               │ should_continue?
        ┌──────┴───────────────────────┐
        │ tool_calls 있음 & steps<MAX   │ 없음 / steps>=MAX
        ▼                               ▼
  ┌─────────────┐                    ┌──────┐
  │  call_tools │  (도구 실행,        │ END  │
  │             │   tool_log·steps++) └──────┘
  └──────┬──────┘
         └────────▶ (다시 call_model)
```

- **노드 `call_model`**: 현재 messages + 도구 스키마로 LLM 호출. tool_calls 가 있으면 그대로 state.messages 에 적재, 없으면 그 내용이 최종 answer.
- **노드 `call_tools`**: 요청된 각 tool_call 을 실행 → ToolMessage 로 messages 에 추가, `tool_log`·`steps` 갱신.
- **조건 엣지 `should_continue`**: tool_calls 존재 && `steps < AGENT_MAX_STEPS` → `call_tools`, 아니면 `END`.
- **max_steps 도달 시**: 최소 우아한 실패 — "확정 못 함 + 지금까지 관찰(tool_log 요약)" 안내(완전판은 Phase 4).
- **LLM 바인딩 결정 필요(아래 7번)**: `langchain-litellm`(ChatLiteLLM.bind_tools) vs `call_model` 에서 litellm.completion 직접 호출.

엣지: `START → call_model`, `call_model →(cond) call_tools|END`, `call_tools → call_model`.

---

## 6. POST /ask 교체 (api/main.py)

```python
@app.post("/ask")
def ask_agent(request: AskRequest) -> AskResponse:
    state = build_initial_state(request.question, request.company, request.year)
    final = agent_graph.invoke(state)
    return AskResponse(answer=final["answer"], sources=final["sources"])
```
- 응답 스키마(`answer`, `sources`)는 유지 → 기존 클라이언트 호환.
- (선택) `tool_log` 를 응답에 포함해 라우팅 과정을 데모로 노출 가능.

---

## 7. 착수 전 결정 필요 (open questions)

1. **LLM↔LangGraph 도구 바인딩 방식**
   - (A) `langchain-litellm` 의 `ChatLiteLLM(...).bind_tools(...)` — LangGraph 표준 패턴, 의존성 1개 추가.
   - (B) `call_model` 노드에서 `litellm.completion(tools=...)` 직접 호출 — 의존성 최소, 도구 파싱 수동.
   - 👉 제안: **(A)** — 그래프 표준 패턴이라 면접 설명·확장에 유리. (CLAUDE.md "LiteLLM 게이트웨이" 원칙과도 부합)
2. **doc_search 비용** — 도구 호출마다 임베딩+리랭킹이 돈다. max_steps 로 상한은 있음. 캐싱은 Phase 4 이후.
3. **회사/연도 추출** — 요청의 `company/year` 필터를 도구 인자 기본값으로 줄지, LLM 이 질문에서 뽑게 할지.
   👉 제안: 둘 다 — 요청 필터가 있으면 우선, 없으면 LLM 이 인자로 채움.
4. **corp_code 해석** — financial_lookup 이 회사명→corp_code 를 매번 corpCode.xml 에서? 작은 캐시 맵 1회 로드 권장.

---

## 8. 작업 순서 (각 단계 ruff·pytest → 커밋)

1. `agent/tools.py` financial_lookup + 표준계정 정규화 + `tests/test_tools.py`(픽스처)
2. compute_change + facts.extract_change + 테스트
3. doc_search 래퍼 + 테스트(retriever 모킹)
4. `agent/state.py` + `agent/graph.py`(가짜 LLM 주입 테스트로 라우팅 검증)
5. `POST /ask` 교체 + 엔드투엔드 수동 확인(서술/숫자/증감/하이브리드 4종 질문)
6. CLAUDE.md 상태 갱신 + 커밋·푸시

## 9. 완료 기준 (DoD)
- 서술형 → doc_search, 숫자형 → financial_lookup(+compute_change) 로 **도구를 옳게 고른다**.
- 하이브리드("실적 악화 원인?") 에서 수치·본문 도구를 **둘 다** 호출해 종합한다.
- `financial_lookup` 은 텍스트가 아닌 **구조화 값**을 반환한다.
- 도구 호출 과정이 `tool_log` 로 보인다. 어떤 질문도 max_steps 안에서 종료한다.
- ruff·pytest 통과(키·DB·모델 없이).
