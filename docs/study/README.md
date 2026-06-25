# 📚 기술 스택 심화 학습 시리즈 (filing-agent)

> **목적** — 이 프로젝트에서 실제로 쓴 기술을 "사용해봤다"고 면접에서 자신 있게,
> 그리고 **원리까지** 말할 수 있을 만큼 깊게 정리한 학습 자료.
> 각 문서는 읽고 → 가리고 답해보고 → 암기 카드로 복습하는 흐름으로 쓰도록 구성.

## 📖 각 문서의 통일 형식

모든 기술 항목은 같은 틀로 적혀 있다:

1. **한 줄 정의** — 면접에서 첫 문장으로 쓸 수 있는 정의
2. **왜 존재하나 / 어떤 문제를 푸나** — 동기
3. **작동 원리 (메커니즘)** — *여기가 핵심*. "안다"와 "써봤다"를 가르는 부분
4. **이 프로젝트에서 실제 사용** — 코드 파일 위치까지 (← "정말 써봤다"의 근거)
5. **면접 Q&A** — 실제 나오는 질문 + 모범 답변 뼈대
6. **함정 / 트레이드오프** — 깊이의 증거
7. **🎴 암기 카드** — 빠른 복습용 한 줄들

## 🗂️ 문서 목록 (추천 학습 순서)

| # | 파일 | 다루는 것 | 면접 중요도 |
|---|---|---|---|
| 01 | [python_tooling.md](01_python_tooling.md) | Python 3.12, uv, ruff, pytest, 타입힌트/TypedDict/Pydantic | ★★ |
| 02 | [fastapi_web.md](02_fastapi_web.md) | FastAPI, ASGI/uvicorn, REST, Pydantic Settings | ★★★ |
| 03 | [rag_and_embeddings.md](03_rag_and_embeddings.md) | RAG, 임베딩, 벡터 유사도, 청킹 | ★★★★★ |
| 04 | [pgvector_and_indexing.md](04_pgvector_and_indexing.md) | pgvector, HNSW vs IVFFlat, 거리척도, ANN | ★★★★ |
| 05 | [hybrid_search_and_reranking.md](05_hybrid_search_and_reranking.md) | BM25, dense vs sparse, 하이브리드, RRF, bi vs cross-encoder | ★★★★★ |
| 06 | [llm_gateway_and_prompting.md](06_llm_gateway_and_prompting.md) | LiteLLM, 프롬프팅, function calling, 구조화 출력 | ★★★★ |
| 07 | [infra_docker_postgres.md](07_infra_docker_postgres.md) | Docker/Compose, WSL2, PostgreSQL, psycopg v3 | ★★★ |
| 08 | [data_dart_ingestion.md](08_data_dart_ingestion.md) | OpenDART API, 캐싱, 파싱, CFS/OFS | ★★ |
| 09 | [interview_qbank.md](09_interview_qbank.md) | 도메인 통합 면접 질문 은행 | ★★★★★ |

> ★★★★★ 우선순위(03, 05, 09)는 이 프로젝트의 **차별화 지점**이라 면접관이 가장 깊게 파고드는 곳.

## 🎯 이 프로젝트의 "한 문장 피치"

> "한국 전자공시(DART)를 대상으로 **하이브리드 검색 + 리랭킹 RAG**를 직접 구현하고,
> 그 위에 **정형(재무수치)/비정형(서술) 데이터를 도구로 라우팅하는 에이전트**를 얹어
> 단순 RAG 챗봇과 차별화한 AI 엔지니어링 포트폴리오."

## ⚠️ 정직성 원칙

- 이 문서로 공부해서 **이해한 만큼만** "써봤다"고 말한다.
- 각 문서의 "이 프로젝트에서 실제 사용" 절은 **진짜 코드 위치**를 가리킨다 → 면접에서 코드를 열어 보여줄 수 있다.
- 아직 구현 전인 것(LangGraph 에이전트·평가·관측)은 "설계했고 진행 중"이라고 정확히 말한다.

---

*관련 문서: 프로젝트 전체 계획은 [../plan.md], 환경 세팅은 [../SETUP.md], 넓은 개요는 [../tech_stack_guide.md].*
