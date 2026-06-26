# Phase 5 설계서 — 평가(Eval) 파이프라인

> 작성일: 2026-06-26 · 상태: **설계 확정 대기(구현 전)**
> 근거: `docs/plan.md` Phase 5. 이 문서는 "골든셋·지표·러너·회귀 테스트"를 먼저 합의하기 위한 것.
> 검증 후 구현 착수.

## 1. 목표 & 범위

**목표** — "프롬프트·검색·라우팅을 바꿨더니 더 좋아졌는가?"를 **숫자로** 답한다. 재무 골든셋을 만들고,
견고한 결정론 지표(숫자 정답률·라우팅 정확도·Hit@k·MRR)를 전면에 두며, 회귀 테스트로 품질 저하를 잡는다.

| 들어가는 것 (Phase 5) | 빠지는 것 (Phase 6으로) |
|---|---|
| 골든셋(goldset.jsonl) — 6유형 | Langfuse 관측 |
| 결정론 지표(metrics.py): 숫자 정답률·라우팅 정확도·Hit@k·MRR | Docker·CI 워크플로 파일 자체 |
| 러너(runner.py) + CLI(`scripts/run_eval.py`) — 점수표 1명령 | (지표를 CI에 *연결*하는 건 Phase 6) |
| 회귀 테스트(키·모델 없이 도는 게이트) | — |
| (선택) LLM-judge·RAGAS/DeepEval 어댑터 — 얇게/수동 | faithfulness 본격 도입 |

> plan.md 원칙: **견고한 결정론 지표를 전면에**, LLM-judge·faithfulness는 보조. 작은 N에서도 덜 흔들린다.

---

## 2. ⚠️ 핵심 설계 긴장 (가장 먼저 합의할 것)

**문제**: 평가는 본질적으로 **에이전트를 실제로 돌려야** 한다(LLM + DART 데이터 + pgvector 필요).
그런데 CLAUDE.md 원칙은 **"테스트는 키·DB·모델 없이 통과"**다. 둘을 한 덩어리로 두면 CI가 못 돈다.

**해결 — 2층 분리(제안)**:
1. **채점 로직(순수 함수) = `metrics.py`**: 예측·정답을 받아 점수를 내는 **순수 함수**. 키·모델·DB 불필요 → CI에서 단위 테스트.
2. **실행(러너) = `runner.py` + `scripts/run_eval.py`**: 골든셋을 **실제 에이전트로 돌려** 예측을 만든다.
   키·DB·데이터 필요 → **로컬/수동**. CI 스모크엔 넣지 않는다.
3. **회귀 테스트 = `tests/test_eval_regression.py`**: ① `metrics.py` 채점 로직이 맞는지 +
   ② **픽스처로 모킹한 도구 슬라이스**(financial_lookup → 기대값)만 키 없이 검증. 전체 에이전트 평가는 게이트하지 않는다.

> 즉 "점수표 출력"(러너)과 "회귀 게이트"(순수 채점 + 모킹 슬라이스)를 분리한다.
> 전체 에이전트 회귀를 CI에 넣는 건 키·비용 때문에 Phase 6에서 별도 판단.

---

## 3. 만들 / 수정할 파일

| 파일 | 신규/수정 | 역할 |
|---|---|---|
| `eval/goldset.jsonl` | 신규 | 질문-정답-출처(6유형). 검증된 시드 + 수집 후 확장 |
| `eval/schema.py` | 신규 | 골든셋/예측 레코드 TypedDict + 로더(jsonl) |
| `eval/metrics.py` | 신규 | **순수 채점 함수**: 숫자 정답률·라우팅 정확도·Hit@k·MRR·집계 |
| `eval/runner.py` | 신규 | 골든셋 → 에이전트 실행 → 예측 수집 → metrics 채점(로컬) |
| `eval/judge.py` | 신규 | (선택) LLM-as-judge: 서술형 보조 지표. 키 있을 때만 |
| `scripts/run_eval.py` | 신규 | CLI 진입점 — "1명령 점수표" |
| `tests/test_metrics.py` | 신규 | 채점 함수 단위 테스트(키·모델 없이) |
| `tests/test_eval_regression.py` | 신규 | 회귀 게이트(픽스처 도구 슬라이스 + 채점 로직) |
| `tests/fixtures/goldset_sample.jsonl` | 신규 | 회귀용 소형 결정론 슬라이스(모킹 대조) |

> RAGAS/DeepEval은 의존성·LLM 호출이 무거워 **이번 범위 밖(또는 얇은 선택 어댑터)**. 결정 필요(9장 #1).

---

## 4. 골든셋 (eval/goldset.jsonl)

plan.md의 6유형. **양보다 질** — 엣지케이스(연결/별도, 하이브리드)를 의도적으로 배치.

| type | 검증 방식 | 정답 필드 |
|---|---|---|
| `lookup` | 숫자 결정론 대조 | `expected_value` |
| `calc` | 숫자 결정론 대조(증감) | `expected_value` |
| `routing` | 도구 선택 일치 | `expected_tools` |
| `combine` | 숫자 결정론 대조(합) | `expected_value` |
| `hybrid` | 도구 선택(복수) + 출처 | `expected_tools` |
| `edge` | 연결/별도 폴백 등 | `expected_value` / `note` |

레코드 스키마(예):
```json
{"id":"q001","type":"lookup","question":"삼성전자가 공시한 2024년 매출액은?",
 "company":"삼성전자","year":2024,
 "expected_value":300870903000000,"expected_tools":["financial_lookup"],
 "relevant_company":"삼성전자","relevant_year":2024}
{"id":"q005","type":"hybrid","question":"삼성전자 2024년 실적 관련 위험은?",
 "company":"삼성전자","year":2024,
 "expected_tools":["financial_lookup","doc_search"],
 "relevant_company":"삼성전자","relevant_year":2024}
```

- ⚠️ **출처 매칭은 (corp_name, year) 튜플로**. 인덱서가 넣는 source 문자열은
  `f"{company} 사업보고서 {year}"`(예: `"삼성전자 사업보고서 2024"`, **공백** 구분)이고 한 공시의 모든 청크가
  공유한다. 자유형 문자열을 직접 비교하면 형식 어긋남으로 Hit@k가 0이 되므로, 골든셋은
  `relevant_company`·`relevant_year`를 쓰고 검색 결과의 `corp_name`·`year` 컬럼과 대조한다.
- **시드 채우기**: 픽스처로 검증된 값(삼성전자 2024 매출액 300,870,903,000,000 등)부터.
  나머지 기업은 **수집(키 필요) 후** 채운다. → 결정 필요(9장 #3).
- **N 규모 솔직 프레이밍**: 40개 안팎 = 통계적 유의성 아닌 **방향성**. README에 명시.

---

## 5. 지표 (eval/metrics.py) — 순수 함수

```python
def number_accuracy(preds, gold) -> float:
    """type∈{lookup,calc,combine,edge} 중 predicted_value == expected_value 비율."""

def routing_accuracy(preds, gold) -> float:
    """predicted_tools(집합) 이 expected_tools 를 만족하는 비율.
    lookup/calc 는 expected 도구가 호출됐는지(recall), hybrid 는 expected 가 모두 호출됐는지."""

def hit_at_k(retrieved: list[tuple], relevant: tuple, k: int) -> float:
    """top-k 의 (corp_name, year) 중 relevant 와 일치가 하나라도 있으면 1.0."""

def mrr(retrieved: list[tuple], relevant: tuple) -> float:
    """첫 relevant (corp_name, year) 일치의 역순위(1/rank). 없으면 0."""

def aggregate(preds, gold, retrievals=None) -> dict:
    """{number_accuracy, routing_accuracy, hit@k, mrr, n_by_type} 점수표."""
```

- **숫자 대조는 결정론**(Phase 4 verifier 철학 재사용): 예측값 ↔ expected_value 정수 비교.
- ⚠️ **combine(합계) 처리**: 합계는 figure에 없고 LLM이 답변 텍스트에서 산술한 값이라 신뢰하지 않는다.
  러너가 **facts의 개별 value를 직접 합산**해 `predicted_value`로 쓴다(결정론 유지). 별도 compute_sum 도구는
  Phase 5 범위 밖(필요 시 Phase 3 패턴으로 추가). → 합계 산술도 LLM이 아니라 평가 코드가 한다.
- 입력은 **이미 수집된 예측/정답** → 순수 함수라 키·모델 없이 테스트 가능.

---

## 6. 러너 (eval/runner.py) + CLI

```python
def run_goldset(graph, items) -> list[Prediction]:
    for item in items:
        final = graph.invoke(build_initial_state(item))
        facts = final["facts"]
        yield Prediction(
            id=item["id"], type=item["type"],
            predicted_tools=[lg["tool"] for lg in final["tool_log"] if lg["ok"]],
            predicted_value=_predicted_value(item["type"], facts),  # combine=합산, 그 외=단일
            answer=final["answer"],
        )
```

- `_predicted_value`: `combine` 이면 facts 의 value 들을 **합산**, 그 외엔 단일 value(없으면 None).
- `scripts/run_eval.py`: 골든셋 로드 → `get_graph()` 로 실행 → `metrics.aggregate` → 점수표 출력(+JSON 저장).
- **Hit@k/MRR**: 검색 품질은 `retriever.search()` 를 골든셋 질문에 **직접** 돌려 결과의
  `(corp_name, year)` 리스트를 모아 `relevant_company`·`relevant_year` 와 대조(에이전트 우회 — 검색 계층만 정밀 측정).
- 러너는 키·DB·데이터 필요 → **로컬 전용**. CI 비포함.

---

## 7. 회귀 테스트 (tests/test_eval_regression.py) — 키 없이

CI 게이트는 두 가지만 본다(전체 에이전트 회귀 아님):
1. **채점 로직 정합성**: `metrics.py` 가 알려진 예측/정답에 기대 점수를 낸다.
2. **결정론 도구 슬라이스**: `fixtures/goldset_sample.jsonl` 의 lookup 항목을 **모킹된 DART 페이로드**로
   `financial_lookup` 직접 호출 → `expected_value` 와 일치하는지. (Phase 3 `test_tools.py` 패턴 재사용)

```python
def test_lookup_slice_matches_expected():
    for item in load_sample():           # 픽스처 jsonl
        with patch(...corp_code...), patch(...fetch_single_account=fixture):
            result = financial_lookup.invoke({...})
        assert result["value"] == item["expected_value"]

def test_number_accuracy_scoring():
    assert number_accuracy(preds, gold) == 1.0   # 알려진 입력
```

> 기준선(baseline) 점수 비교는 러너 산출 JSON 으로 **로컬**에서. CI 게이트는 위 결정론 슬라이스만.

---

## 8. 작업 순서 (각 단계 ruff·pytest → 커밋)

1. `eval/schema.py`(레코드 타입 + jsonl 로더) + `eval/goldset.jsonl` 시드(검증된 값).
2. `eval/metrics.py`(순수 함수) + `tests/test_metrics.py`.
3. `tests/fixtures/goldset_sample.jsonl` + `tests/test_eval_regression.py`(모킹 슬라이스 + 채점).
4. `eval/runner.py` + `scripts/run_eval.py`(로컬 실행 경로; 키 있을 때 수동 점수표 확인).
5. (선택) `eval/judge.py` 인터페이스.
6. README에 개선 전/후(방향성) 표 자리 + 한계 프레이밍. CLAUDE.md 상태 갱신 + 커밋.

---

## 9. 결정 사항 (확정됨)

1. **RAGAS/DeepEval 범위** — ✅ **(A) 결정론 지표만 직접 구현**. RAGAS/DeepEval은 범위 밖(키·비용·의존성
   무게 회피, plan.md "견고 지표 전면"). 필요 시 나중에 얇은 어댑터.
2. **CI 회귀 범위** — ✅ **(A) 순수 채점 + 모킹 도구 슬라이스만 키 없이**. 프로젝트 원칙(키·DB·모델 없이 통과) 준수.
3. **골든셋 채우기** — ✅ **(A) 구조 + 검증된 시드(픽스처값) 커밋, 나머지는 수집 후 로컬 확장**.
4. **LLM-judge** — ✅ **(A) `judge.py` 인터페이스만, 서술형 보조·키 있을 때 선택**(CI 비포함).
5. **Hit@k/MRR 측정 경로** — ✅ **(A) retriever 직접 호출로 검색 계층만 측정**(에이전트 우회, 정밀).

### 추가 수정(자체 검증에서 발견)
- 출처 매칭을 자유형 문자열 → **(corp_name, year) 튜플**로 변경(실제 source 형식 `"{company} 사업보고서 {year}"`와의 어긋남으로 Hit@k=0 방지).
- combine 합계를 **러너가 facts에서 직접 합산**(LLM 산술 불신, 결정론 유지).

---

## 10. 완료 기준 (DoD)

- `python scripts/run_eval.py` 한 명령으로 **점수표**(숫자 정답률·라우팅 정확도·Hit@k·MRR·유형별 N) 출력(로컬, 키 필요).
- 설정(Phase 2~3 토글) 변경 시 점수 변화를 비교할 수 있다.
- 회귀 테스트가 **키·모델·DB 없이** 통과(채점 로직 + 모킹 도구 슬라이스).
- 골든셋이 6유형(특히 hybrid·edge)을 포함한다.
- ruff·pytest 통과. 채점 로직은 순수 함수로 분리.
