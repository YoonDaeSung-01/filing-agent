# Phase 4 설계서 — 하네스 & 루프 (검증 루프 · 가드레일 · 우아한 실패)

> 작성일: 2026-06-26 · 상태: **설계 확정 대기(구현 전)**
> 근거: `docs/plan.md` Phase 4. 이 문서는 Phase 3 ReAct 그래프 위에 "검증 루프·가드레일·우아한 실패"를
> 어떻게 얹을지 먼저 합의하기 위한 것. 검증 후 구현 착수.

## 1. 목표 & 범위

**목표** — 에이전트를 감싸는 안전장치. 답변(특히 숫자)이 기준을 통과하는지 **결정론적으로** 검증해 자기 교정하고,
폭주를 막는 예산·종료 조건을 두며, 악성 입력을 가드레일로 차단한다.

| 들어가는 것 (Phase 4) | 빠지는 것 (Phase 5로) |
|---|---|
| 검증 루프(verifier) — 숫자 답변을 조회값과 결정론 대조 | LLM-judge·골든셋 평가 |
| 루프 계약(max_steps·budget·종료조건) State화 | RAGAS/DeepEval faithfulness |
| 우아한 실패 템플릿(부분 결과 + 다음 행동) — 완전판 | 회귀 테스트 CI |
| 가드레일(입력: 인젝션·투자조언 선회 / 출력: 출처·형식) | Langfuse 관측(Phase 6) |

> 원칙(CLAUDE.md): 숫자 답변 검증은 **LLM-judge가 아니라 조회된 실제 값과 결정론적으로 대조**한다.
> verifier를 완벽히 만들려 하지 말 것 — "숫자가 facts와 일치하고 출처가 있는지" 단순 규칙으로 시작해 강화.

---

## 2. ⚠️ 핵심 설계 간극 (가장 먼저 합의할 것)

**문제**: 검증 루프가 "답변의 숫자 == 조회된 실제 값"을 대조하려면 **구조화된 조회값(facts)**이 필요하다.
그런데 현재 Phase 3 그래프(`agent/graph.py`)에서 `financial_lookup`·`compute_change`의 결과는
**`ToolMessage`의 JSON 문자열**로만 남는다(`_node_call_tools`). 검증 노드가 대조할 깨끗한 타입 값이 State에 없다.

**해결 방향(제안)**: `call_tools`가 수치 도구 성공 결과를 **State의 `facts` 리스트에 구조화 값으로 적재**한다
(`operator.add` 리듀서로 누적). 그러면 verifier는 텍스트를 다시 파싱하지 않고 `state["facts"]`와 대조한다.
이게 plan.md·`개인 프로젝트`(Notion) 설계 노트가 말한 "facts는 검증의 결정론적 근거" 패턴이다.

> 이 결정이 Phase 4 전체의 토대다. 아래 4·8장이 모두 여기에 의존한다.

---

## 3. 만들 / 수정할 파일

| 파일 | 신규/수정 | 역할 |
|---|---|---|
| `harness/__init__.py` | 기존(빈 패키지) | — |
| `harness/verifier.py` | 신규 | 결정론 검증: 답변 숫자 ↔ facts 대조 + 출처 유무. 순수 함수 위주 |
| `harness/guardrails.py` | 신규 | 입력(인젝션 차단·투자조언 선회·길이) / 출력(출처·형식) 가드 |
| `harness/contract.py` | 신규 | 루프 계약 상수/구조(max_steps·verify 예산·종료조건) 한 곳에 |
| `agent/state.py` | 수정 | `facts`(리듀서)·`draft`·`figures`·`verifier_feedback`·`verify_attempts`·`status` + `AnswerSchema`/`Figure` |
| `agent/tools.py` | 수정 없음(반환 구조 그대로 활용) 또는 facts 키 정규화 헬퍼 추가 |
| `agent/graph.py` | 수정 | 노드 추가(input_guard·finalize·verify·output_guard·graceful_fail), `call_tools`가 facts 적재 |
| `config.py` | 수정 | `agent_max_verify_attempts`(검증 재시도 예산) 추가 |
| `tests/test_verifier.py` | 신규 | 숫자 대조·출처 검사 순수 로직(모델·DB 불필요) |
| `tests/test_guardrails.py` | 신규 | 인젝션 패턴·투자조언 선회·출력 출처 검사 |
| `tests/test_graph.py` | 신규(또는 보강) | 가짜 LLM 주입으로 retry→ok / giveup→graceful_fail 라우팅 검증 |

---

## 4. 검증 루프 (harness/verifier.py)

LLM-judge 아님. **결정론 규칙**으로 시작한다(plan.md DoD: "근거 없이 숫자를 지어내면 검증 루프가 잡는다").

### 4.1 검증 대상 두 가지
1. **숫자 답변**: 초안에 등장하는 금액 토큰이 `state["facts"]`의 어떤 `value`와 일치하는가.
2. **출처**: 답변에 출처(보고서·연도) 인용이 1개 이상 있는가.

### 4.2 순수 함수 시그니처(안)
```python
def extract_numbers(text: str) -> list[int]:
    """답변 텍스트에서 금액 후보(콤마/원 단위)를 정수로 추출."""

def numbers_supported(draft: str, facts: list[dict], *, tolerance: int = 0) -> bool:
    """draft의 모든 금액 토큰이 facts의 value(또는 delta 등)에 존재하면 True.
    facts가 비어 있는데 숫자를 주장하면 False(= 환각 의심)."""

def has_source(draft: str) -> bool:
    """'출처'/'보고서'/연도 패턴 등 인용 표지가 있으면 True."""

def verify(draft: str, facts: list[dict]) -> tuple[bool, str]:
    """(통과여부, 실패사유). 실패사유는 재시도 피드백으로 agent에 되돌린다."""
```

### 4.3 검증 방식 — structured output 채택 (확정)
**결정**: `finalize` 노드에서 `llm.with_structured_output(AnswerSchema)`로 답변을 받아,
주장 숫자를 **정수 필드**로 가져와 facts와 **정수 대 정수**로 정확 대조한다. 정규식 파싱 늪을 피한다.

```python
class Figure(TypedDict):
    account: str
    year: int
    value: int     # 원 단위 정수 (LLM이 주장한 값)
    source: str

class AnswerSchema(TypedDict):
    answer: str            # 사용자에게 보일 산문 답변
    figures: list[Figure]  # 답변이 인용한 수치(검증 대상)
```

- **verify**: `figures`의 각 `value`가 `state["facts"]`의 어떤 value와 일치하는지 정수 대조.
  facts가 비었는데 `figures`가 숫자를 주장하면 실패(환각 의심). `figures`가 비고 순수 서술 답변이면 출처 표지만 검사.
- **장점**: 한국어 금액표현("약 300조") 파싱 불필요, Phase 5 평가가 동일 필드를 재사용.
- **bind_tools와의 분리**: ReAct 루프 중엔 `bind_tools`(도구 호출), 도구가 끝나면 **별도 finalize 호출**에서
  `with_structured_output`. 한 호출에 두 모드를 섞지 않는다(8장 토폴로지의 finalize 노드).

> 참고: plan.md 4.3은 "정규식 먼저"를 제안했으나, 이 프로젝트의 핵심이 결정론 검증이라
> 처음부터 견고한 structured output을 택한다(정규식 오탐 리스크 회피). 단순 규칙 버전은 폐기.

---

## 5. 우아한 실패 (graceful_fail 노드)

Phase 3엔 `_extract_final`에 최소 버전만 있다. Phase 4에서 **부분 결과 + 부족 사유 + 다음 행동** 3단으로 완성.

```python
def graceful_fail(state: AgentState) -> dict:
    confirmed = summarize_facts(state["facts"])  # 지금까지 확인된 타입 값
    reason = state.get("verifier_feedback") or "검증 한도/스텝 예산 도달"
    answer = (
        "확정된 답을 찾지 못했습니다. "
        f"확인된 부분: {confirmed}. (사유: {reason}) "
        "질문을 회사·연도·계정으로 좁혀 주시면 다시 시도합니다."
    )
    return {"answer": answer, "sources": sources_from_facts(state["facts"])}
```

진입 경로: ① ReAct 도구 예산 초과(`steps >= max_steps`) ② 검증 재시도 예산 초과(`verify_attempts >= max_verify`).

---

## 6. 가드레일 (harness/guardrails.py)

규칙 기반(정규식/키워드) — 싸고 결정론적이라 테스트 가능. LLM 호출 없음.

### 6.1 입력 가드 (input_guard 노드, 그래프 맨 앞)
- **프롬프트 인젝션 차단**: "이전 지시 무시", "ignore previous", "system prompt 보여줘" 등 패턴 → 거절 응답으로 단락(短絡).
- **길이 제한**: 질문 N자 초과 차단.
- **투자조언 선회**: "사야 해?", "매수/매도 추천" 등 → 차단이 아니라 **사실 추출로 선회** 안내
  ("매수 추천은 제공하지 않습니다. 대신 공시된 실적·재무 사실을 알려드릴 수 있습니다").

### 6.2 출력 가드 (output_guard 노드, END 직전)
- **출처 검증**: 숫자/사실 답변에 출처 표지가 없으면 가드가 부가하거나 경고.
- **형식/민감정보**: 길이·형식 최종 점검(현재 범위에선 가볍게).

### 6.3 반환 계약
가드는 `{"action": "pass"}` 또는 `{"action": "block", "answer": <안내문>}` 같은 구조로 반환 →
그래프 조건 엣지가 block이면 바로 END로 보낸다(에이전트·도구 호출 없이).

---

## 7. State 확장 (agent/state.py)

```python
class AgentState(TypedDict):
    question: str
    company: str | None
    year: int | None
    messages: Annotated[list[AnyMessage], add_messages]
    tool_log: list[dict]
    steps: int
    # ── Phase 4 추가 ──
    facts: Annotated[list[dict], operator.add]  # 수치 도구 성공 결과 누적(검증 근거)
    draft: str | None                            # finalize가 낸 산문 답변(AnswerSchema.answer)
    figures: list[dict]                          # finalize가 낸 주장 수치(AnswerSchema.figures, 검증 대상)
    verifier_feedback: str | None                # 검증 실패 피드백(재시도 시 agent에 전달)
    verify_attempts: int                         # 검증 재시도 카운터(별도 예산)
    status: str | None                           # "ok" | "retry" | "giveup" — 라우팅용
    answer: str | None
    sources: list[str]
```

`AnswerSchema`/`Figure` TypedDict는 `agent/state.py`(또는 `agent/schema.py`)에 둔다(4.3 정의).

`config.py`: `agent_max_verify_attempts: int = 2` 추가(검증 재시도 상한, tool 예산과 분리).

---

## 8. 그래프 토폴로지 변경 (agent/graph.py)

Phase 3: `START → call_model →(cond) call_tools|extract_final → END`
Phase 4: 가드 2개 + finalize + 검증 루프를 끼운다.

```
START → input_guard ─(block)──────────────────────────────────────► END
           │(pass)
           ▼
        call_model ──(tool_calls 있음)──► call_tools ──(steps<MAX)──► call_model
           │(도구 호출 없음 = 추론 종료)      (facts·tool_log·steps++) │
           │                                                   (steps>=MAX)
           ▼                                                        ▼
        finalize ── with_structured_output → {answer, figures}  graceful_fail → END
           ▼
         verify ──(ok)──► output_guard ──► END
           │ │
           │ └─(giveup: verify_attempts>=MAX)──► graceful_fail ──► END
           ▼
        (retry: feedback를 새 메시지로 추가) ──► call_model
```

- **input_guard**: 인젝션/투자조언/길이. block이면 `status` 세팅 후 바로 END 분기.
- **call_model**: tool_calls가 **있으면 항상 call_tools로**(예산 판정은 여기서 하지 않음 — dangling
  tool_calls가 finalize에 닿지 않게). 없으면 finalize. ReAct 루프 동안 `bind_tools`만 사용.
- **call_tools**: 도구 실행 + 수치 도구 성공 시 `facts`에 적재(2장). 실행 후 `steps>=MAX`면 graceful_fail,
  아니면 call_model. → tool_calls는 **항상 ToolMessage로 해소된 뒤** finalize에 도달.
- **finalize**: 도구 호출이 끝나면 `with_structured_output(AnswerSchema)`로 `{answer, figures}` 생성 →
  `draft`(answer)·figures를 State에. 여기서만 structured output 사용.
- **verify**: `figures`의 value를 `facts`와 정수 대조 + 출처 검사 → `status` = ok/retry/giveup.
  retry면 `verifier_feedback`를 다음 `call_model` 입력 메시지에 추가.
- **graceful_fail / output_guard**: 5·6장.
- **종료 보장**: tool 예산(`steps`)과 verify 예산(`verify_attempts`) 둘 다 상한 → 모든 사이클이 반드시 END.

> Phase 3의 `extract_final`은 finalize + output_guard로 대체된다(제거).

---

## 9. 결정 사항 (확정됨)

1. **facts 적재 방식** (2장) — ✅ **(A) `call_tools`가 State `facts`에 구조화 적재(리듀서)**. 검증·평가 모두에 깨끗.
2. **숫자 검증 강도** (4.3) — ✅ **(B) `with_structured_output(AnswerSchema)`로 처음부터 견고하게**.
   정규식 오탐 리스크를 피하고 결정론 검증을 실제로 견고하게. finalize 노드로 bind_tools와 분리.
3. **가드레일 구현** (6장) — ✅ **규칙 기반(정규식/키워드)**. 결정론·테스트 용이.
4. **verify 재시도 예산** — ✅ **별도 카운터(`agent_max_verify_attempts`, 기본 2)**. tool `steps` 예산과 분리.
5. **투자조언 처리 위치** — ✅ **input_guard에서 선회** + 시스템 프롬프트 이중 방어.

---

## 10. 작업 순서 (각 단계 ruff·pytest → 커밋)

1. `agent/state.py` 확장 + `config.py` 예산 + `harness/contract.py`.
2. `harness/verifier.py`(순수 함수) + `tests/test_verifier.py`(숫자 대조·출처·오탐 방지).
3. `harness/guardrails.py` + `tests/test_guardrails.py`(인젝션·투자조언·출력 출처).
4. `agent/graph.py`: `call_tools` facts 적재 → verify·guard·graceful_fail 노드/엣지 배선.
5. `tests/test_graph.py`: 가짜 LLM 주입으로 retry→ok / giveup→graceful_fail / 인젝션 block 라우팅.
6. 엔드투엔드 수동 확인(정상 숫자 / 환각 유도 / "이전 지시 무시" / 투자조언 / max_steps 폭주).
7. CLAUDE.md 상태 갱신 + 커밋·푸시.

---

## 11. 완료 기준 (DoD)

- 근거(facts) 없이 숫자를 지어내려 하면 **검증 루프가 잡아 재시도하거나 우아한 실패**로 응답한다.
- "이전 지시 무시" 류 입력이 input_guard에서 **차단**된다.
- 투자조언 요청이 **사실 추출로 선회**된다(거절이 아니라 대안 제시).
- 어떤 질문도 tool 예산·verify 예산 안에서 **반드시 종료**하고, 막히면 부분 결과+다음 행동을 준다.
- 숫자 검증은 LLM이 아니라 **facts와 결정론적으로 대조**한다.
- ruff·pytest 통과(키·DB·모델 없이). 검증/가드 로직은 순수 함수로 분리해 단위 테스트.
