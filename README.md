# filing-agent

DART(한국 전자공시) 자료를 근거로 재무 질문에 **출처와 함께** 답하는 에이전트. 질문 성격에 따라 공시 본문을
의미 검색하거나, 재무 수치를 구조화 조회·계산해 답한다.

> **이 도구는 투자 조언이 아니라 공시 사실 추출 도구입니다.** "이 주식 사야 하나?" 같은 매수·매도 추천에는
> 답하지 않습니다. 공시에 기재된 사실(재무 수치 등)을 출처와 함께 추출·전달하는 것만 목표로 합니다.

## 무엇을 하는가

단순 RAG 챗봇과 세 가지가 다르다.

1. **도구 라우팅 에이전트** — 답을 바로 내지 않고, 질문에 맞는 도구(본문 검색·수치 조회·증감 계산)를
   에이전트가 고르고, 하이브리드 질문이면 여러 도구를 모아 종합한다.
2. **하네스(검증 루프·가드레일)** — 숫자 답변이 실제 조회값·출처를 인용하는지 **결정론적으로** 검증해
   자기 교정하고, 예산·종료 조건으로 폭주를 막으며, 프롬프트 인젝션을 차단한다.
3. **평가 파이프라인** — "프롬프트·검색·라우팅을 바꿨더니 좋아졌는가?"를 숫자(정답률·라우팅 정확도·Hit@k·MRR)로
   측정하고, 회귀 테스트로 품질 저하를 잡는다.

## 아키텍처

요청 한 건이 흐르는 경로:

```
질문 → 입력 가드레일 → 에이전트(LangGraph: 도구 선택·종합) → finalize(구조화 출력)
       → 검증 루프(숫자↔조회값 결정론 대조) → 출력 가드레일 → 답변 + 출처
       (전 과정을 Langfuse 트레이스로 기록, 키 있을 때)
```

| 계층 | 구현 |
|---|---|
| API | FastAPI |
| 에이전트 | LangGraph ReAct (`doc_search` / `financial_lookup` / `compute_change`) |
| 검색(비정형) | pgvector 벡터 + BM25 하이브리드(RRF 융합) + BGE-reranker-v2 리랭킹 |
| 수치(정형) | DART 주요계정 구조화 조회 + 도구 내부 증감 계산 |
| 하네스 | 검증 루프 + 가드레일 + 우아한 실패 |
| 평가 | 골든셋 + 결정론 지표 + 회귀 테스트 |
| 관측·운영 | Langfuse(선택) + Docker + GitHub Actions CI |
| LLM 게이트웨이 | LiteLLM (공급자 교체 용이) |

## 빠른 시작 (로컬)

요구사항: [uv](https://docs.astral.sh/uv/), Docker(벡터 DB용).

```bash
# 1) 의존성 동기화
uv sync

# 2) 인증키 설정: .env.example 을 복사해 키를 채운다.
#    DART 키: https://opendart.fss.or.kr (무료)  |  LLM 키: OpenAI/Anthropic
cp .env.example .env          # PowerShell: Copy-Item .env.example .env

# 3) 벡터 DB 기동(pgvector)
docker compose up -d pgvector

# 4) 데이터 수집 + 인제스트(임베딩 → pgvector)
uv run python scripts/ingest_all.py

# 5) 서버 실행
uv run uvicorn filing_agent.api.main:app --reload
```

## 빠른 시작 (Docker)

앱과 벡터 DB를 한 번에 띄운다. `.env`만 준비하면 된다.

```bash
docker compose up --build
```

`http://localhost:8000/health` 가 `{"status":"ok"}` 를 반환하면 정상이다.

## 엔드포인트

- `GET /health` → `{"status":"ok"}` — 키 불필요.
- `POST /ask` — 에이전트 질의응답. 본문: `{"question": "...", "company": "삼성전자", "year": 2024}`.
  응답: `{"answer", "sources", "tool_log"}` (`tool_log` 로 도구 선택 과정을 노출).
- `GET /ask?company=삼성전자&year=2024` — 단일 매출액 템플릿 답변(초기 걷는 해골 경로).

## 평가

골든셋을 에이전트로 돌려 점수표를 출력한다(키·DB 필요, 로컬 전용).

```bash
uv run python scripts/run_eval.py
```

출력: 숫자 정답률 · 라우팅 정확도 · Hit@k · MRR · 유형별 N. (N이 작아 통계적 유의성이 아니라 **방향성** 지표)

실측 결과(골든셋 9건, 2026-06-26 · 삼성전자 등 제조 대형주 실데이터):

| 지표 | 값 | 비고 |
|---|---|---|
| 숫자 정답률(number_accuracy) | 1.000 | lookup·calc·edge 전부 조회값과 정수 일치 |
| 라우팅 정확도(routing_accuracy) | 0.889 (8/9) | combine(다기업 합산) 1건 미달 — 아래 한계 참조 |

> 라이브 실행으로 검증 루프의 출처 판정 버그(structured output 출처를 산문에서만 찾던 문제)를 발견·수정했다.
> 모킹 테스트만으로는 못 잡았고, 실데이터 1회 실행이 헤드라인 기능(수치+출처)의 회귀를 드러냈다.

## 관측 (선택)

`.env` 에 `LANGFUSE_PUBLIC_KEY`·`LANGFUSE_SECRET_KEY` 를 넣으면 한 질문의 전체 실행(그래프 노드·LLM·도구)이
[Langfuse 클라우드](https://cloud.langfuse.com) 에 트레이스로 기록된다. 키가 없으면 자동으로 비활성화되며
앱은 그대로 동작한다.

## 개발 점검

```bash
uv run ruff check     # 린트
uv run pytest         # 테스트 — 키·DB·모델 없이 통과
```

푸시·PR 마다 GitHub Actions 가 위 두 명령을 자동 실행한다.

## 한계 (솔직한 회고)

- **투자 조언이 아니라 사실 추출 도구**다. 매수·매도 추천에는 답하지 않는다.
- **스코프를 의도적으로 좁혔다**: 제조 대형주 10개 · 계정 5개(매출액·영업이익·당기순이익·자산총계·부채총계).
  목적이 데이터 정제가 아니라 AI 에이전트 증명이라, DART 파싱 늪을 피하려 범위를 잘랐다.
- **평가 N이 작다(40개 안팎)**: 통계적 유의성이 아니라 방향성. 대신 엣지케이스(연결/별도, 하이브리드)를
  의도적으로 배치해 질적 평가에 집중했다.
- **combine(다기업 합산)은 미완성**: "A사와 B사 매출 합산" 같은 다기업 질의는 에이전트가 회사별 조회로
  분해하는 동작이 아직 일관되지 않다(라우팅 평가의 유일한 미달 항목). 단일 기업 조회·계산·검색은 정상.
- **Docker 이미지가 크다(2~3GB)**: 리랭커(torch)를 포함해 자체 완결성을 택한 트레이드오프.
- **연결(CFS)/별도(OFS)**: 기본은 연결 기준, 없으면 별도로 폴백한다.

## 데이터 출처

- **OpenDART** — 금융감독원 전자공시시스템 오픈 API, https://opendart.fss.or.kr
  - 회사 고유번호(corp_code) 매핑: `corpCode.xml`
  - 재무 주요계정: `fnlttSinglAcnt.json`
  - 사업보고서 원문(서술 섹션): `document.xml`
