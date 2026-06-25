# Phase 1 완료 보고서 — 데이터 수집 + 기본 RAG

> 작성일: 2026-06-26 · 상태: **Phase 1 완료, 엔드투엔드 동작 확인**

## 1. 이번 단계에서 한 일

새 노트북(개인 PC)에서 환경을 세팅하고 Phase 1을 완성했다. DART 공시 데이터를 수집·임베딩해 pgvector에 적재하고, `POST /ask`로 공시 본문을 의미 검색해 출처와 함께 답하는 최소 RAG 파이프라인이 실제로 동작하는 것까지 확인했다.

### 구현 모듈

| 모듈 | 역할 |
|---|---|
| `ingest/constants.py` | 대상 10개 제조 대형주 · 5개 계정 · TARGET_YEAR(2024) 상수 |
| `ingest/dart_client.py` | OpenDART API 호출 — corp_code 매핑, 주요계정 조회, 캐싱 |
| `ingest/facts.py` | 재무 수치 → 타입 있는 구조화 값(CFS 우선/OFS 폴백) |
| `ingest/filings.py` | 사업보고서 원문(document.xml ZIP)에서 서술 텍스트 추출·캐싱 |
| `ingest/chunker.py` | 고정 크기 + overlap 청킹 (Phase 2에서 고도화 예정) |
| `ingest/indexer.py` | 청크 임베딩 → pgvector 적재, HNSW 인덱스 |
| `retrieval/retriever.py` | 질문 임베딩 → 코사인 유사도 top-k 검색 |
| `llm/client.py` | LiteLLM 게이트웨이 — 완성·임베딩 추상화, 근거 강제 시스템 프롬프트 |
| `api/main.py` | `GET /health`, `GET /ask`(Phase 0 템플릿), `POST /ask`(RAG) |
| `scripts/ingest_all.py` | 전체 파이프라인: corp_code → 재무 → 서술 → 임베딩 → 적재 |
| `scripts/collect_dart.py` | LLM 키 없이 DART 데이터만 수집·캐싱 (1~3단계) |

### 데이터 적재 결과
- 재무 수치: 10개 기업 × 5개 계정 (당기순이익은 주요계정 API 미제공으로 일부 "없음")
- 서술 텍스트: 9/10개 기업 수집 (LG화학은 document.xml 포맷 이슈로 제외 — Phase 1 수용)
- **벡터 인덱스: 총 14,311개 청크** pgvector 적재 완료

### 사용 스택 (Phase 1 실제)
- 임베딩: OpenAI `text-embedding-3-small`(1536차원). plan.md의 "임베딩만 호스팅 API로 빼 로컬 부담 0" 트레이드오프를 채택 (BGE-M3 로컬은 CPU에서 느림).
- LLM: `gpt-4o-mini` (LiteLLM 경유)
- 벡터DB: pgvector (Docker `pgvector/pgvector:pg17`)

## 2. 환경 트러블슈팅 (새 노트북)

이번 세션에서 막혔던 지점과 해결책. 다음 환경 이전 시 재참고용.

### (1) WSL2 미설치 → Docker Desktop 구동 실패
- 증상: Docker Desktop "Virtualization support not detected"
- 원인: BIOS 가상화는 켜져 있었으나 WSL2 미설치
- 해결: 관리자 PowerShell `wsl --install --no-distribution` → 재시작

### (2) 포트 5432 충돌 (가장 까다로웠던 문제)
- 증상: Docker 컨테이너는 정상인데 Python 연결 시 인증 실패
- 원인: **Windows에 PostgreSQL 16 서비스(`postgresql-x64-16`)가 이미 5432 점유** → Docker 대신 Windows 네이티브 PG로 연결되고 있었음
- 진단: `netstat -ano | findstr :5432` → 두 프로세스(Docker + Windows PG)가 동시 LISTEN
- 해결: `docker-compose.yml` 포트 `5432:5432` → **`5433:5432`**, `config.py`의 `pg_dsn` 기본값도 5433으로 변경

### (3) psycopg2 UnicodeDecodeError (Windows 한국어 locale)
- 증상: `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xb8`
- 원인: psycopg2가 libpq 연결 오류 메시지를 cp949(한국어 Windows)로 받는데 UTF-8로 디코딩 시도 → 정작 진짜 에러(인증 실패)가 가려짐
- 해결: **psycopg2 → psycopg(v3) 전환**. v3는 인코딩을 올바르게 처리해 실제 에러 메시지가 노출됨 → (2)번 포트 충돌을 발견할 수 있었음
- 부수 변경: `indexer.py`를 contextmanager 패턴으로, `setup_table`은 `vector` 확장 생성 **후**에 `register_vector` 호출하도록 순서 분리

### (4) 터미널 인코딩 (cp949) — print 문 깨짐
- `—`(em-dash), 이모지(❌) 등이 PowerShell cp949에서 `UnicodeEncodeError`
- 해결: 스크립트 print 문에서 해당 문자 제거/치환 (`—` → `-`, `❌` → `FAIL`)

## 3. 검증

- `ruff check .` 통과
- `pytest` 10/10 통과
- `POST /ask` 실제 동작 확인:
  - "삼성전자 2024년 매출액?" → "약 300조 8,709억원 (출처: 삼성전자 사업보고서 2024)"
  - 출처(sources) 함께 반환

## 4. 다음 단계 — Phase 2 (RAG 고도화)

plan.md 기준 Phase 2는 **검색 품질 개선**이다 (financial_lookup·LangGraph는 Phase 3).
1. 청킹 개선 — 고정 크기 → 문단/문장 경계 존중
2. 리랭커 — top-20 → BGE-reranker-v2(cross-encoder) → top-5
3. 하이브리드 검색 — 벡터 + BM25 + 메타데이터 필터
4. 개선 전/후 비교 가능하도록 설정값 외부화·기록
