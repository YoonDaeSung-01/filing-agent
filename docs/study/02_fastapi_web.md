# 02. FastAPI · 웹 API (★★★)

> 백엔드 면접 단골. "왜 FastAPI?", "동기 vs 비동기"를 원리로 답할 수 있게.

---

## 2-1. FastAPI

### 한 줄 정의
> Python 비동기 웹 프레임워크. **Starlette(ASGI) + Pydantic** 위에서 타입 힌트로 자동 검증·자동 문서를 제공.

### 작동 원리 (왜 편한가)
- 함수 시그니처의 **타입 힌트**를 읽어:
  - 요청 본문/쿼리를 **자동 파싱·검증**(Pydantic).
  - **OpenAPI 스펙 자동 생성** → `/docs`(Swagger UI), `/redoc`.
- 잘못된 입력은 자동으로 422 + 에러 상세.

### 이 프로젝트에서 실제 사용
- `api/main.py`:
  - `GET /health` — 헬스체크(키 불필요).
  - `GET /ask?company=&year=` — Phase 0 재무 템플릿.
  - `POST /ask` — `AskRequest(question, company?, year?)` → `AskResponse(answer, sources)`.
- 요청/응답을 Pydantic 모델로 선언 → 검증·문서 자동.

### 면접 Q&A
**Q. 왜 FastAPI를 골랐나요?**
> 타입 힌트만으로 입출력 검증과 OpenAPI 문서가 자동 생성되고, 비동기를 지원해 LLM·DB 같은 I/O 바운드 호출에 유리합니다. Pydantic 통합이 강해 API 경계의 데이터 안정성도 좋습니다.

**Q. Flask와 차이는?**
> Flask는 동기·미니멀이라 가볍지만 검증·문서·비동기를 직접 붙여야 합니다. FastAPI는 그게 내장이고 ASGI 기반이라 동시성에 유리합니다.

### 🎴 암기 카드
- FastAPI = Starlette(ASGI) + Pydantic
- 타입힌트 → 자동 검증 + 자동 OpenAPI(/docs)
- 잘못된 입력 → 422 자동

---

## 2-2. ASGI vs WSGI · uvicorn

### 정의
- **WSGI** — 전통적 **동기** Python 웹 서버 규약(Flask/Django 전통). 요청 1개 = 워커 1개가 끝까지 붙듦.
- **ASGI** — **비동기** 규약. I/O 대기 중 다른 요청을 처리 → 동시성↑.
- **uvicorn** — FastAPI 앱을 구동하는 **ASGI 서버**.

### 왜 이 프로젝트에 ASGI가 맞나
- 요청 처리의 대부분이 **I/O 대기**(임베딩 API, LLM 호출, DB 쿼리).
- 동기라면 그 대기 동안 워커가 놀지만, async는 **대기 중 다른 요청**을 처리 → 같은 자원으로 더 많은 동시 요청.

### 동시성 vs 병렬성 (헷갈리는 개념)
- **동시성(concurrency)** — 여러 작업을 번갈아 진행(한 코어에서도 가능, async가 이것).
- **병렬성(parallelism)** — 여러 작업을 진짜 동시에(멀티코어/프로세스).
- I/O 바운드 → 동시성으로 충분, CPU 바운드 → 병렬성 필요.

### 면접 Q&A
**Q. 동기와 비동기 서버 차이는?**
> 동기(WSGI)는 요청이 I/O를 기다리는 동안 워커가 묶입니다. 비동기(ASGI)는 그 대기 시간에 다른 요청을 처리해 같은 자원으로 더 많은 동시 요청을 감당합니다. 저희는 LLM·DB 호출이 I/O 바운드라 ASGI(uvicorn)가 유리했습니다.

**Q. async면 무조건 빠른가요?**
> 아닙니다. I/O 바운드에선 이득이지만, CPU 바운드(예: 리랭킹 추론)는 이벤트 루프를 막아 오히려 해롭습니다. 그건 별도 스레드/프로세스나 워커로 빼야 합니다.

### 🎴 암기 카드
- WSGI=동기, ASGI=비동기, uvicorn=ASGI서버
- async 이득 = I/O 바운드(대기 중 다른 일)
- 동시성(번갈아) ≠ 병렬성(진짜 동시)
- CPU바운드를 async에 넣으면 루프 막힘

---

## 2-3. REST API 기본

### 핵심 개념
- **자원(resource)** 중심 + **HTTP 메서드**로 행위 표현:
  | 메서드 | 의미 | 멱등성 |
  |---|---|---|
  | GET | 조회 | O |
  | POST | 생성/실행 | X |
  | PUT | 전체 교체 | O |
  | PATCH | 부분 수정 | X |
  | DELETE | 삭제 | O |
- **상태 코드**: 2xx 성공, 4xx 클라이언트 잘못(400 검증, 401 인증, 404 없음, 422 검증), 5xx 서버 잘못.
- **무상태(stateless)** — 각 요청이 필요한 정보를 모두 포함(서버가 세션을 안 들고 있어 확장 쉬움).

### 이 프로젝트
- `GET /ask`는 조회성, `POST /ask`는 질의 "실행"(본문에 질문) — 메서드 선택의 의미.

### 면접 Q&A
**Q. GET과 POST를 어떻게 구분하나요?**
> GET은 조회·멱등이고 본문이 없습니다. POST는 생성/실행이고 본문에 데이터를 담습니다. 저희 `POST /ask`는 질문 본문을 받아 검색·생성을 실행하므로 POST가 맞습니다.

**Q. REST vs GraphQL vs gRPC?**
> REST는 단순·캐시 친화적, GraphQL은 클라이언트가 필요한 필드만 받아 오버페치를 줄이고, gRPC는 바이너리(protobuf) 기반 고성능이라 마이크로서비스 간 통신에 강합니다. 이 프로젝트는 단순 질의응답이라 REST면 충분했습니다.

### 🎴 암기 카드
- 자원 + HTTP메서드, 무상태
- 2xx/4xx(클라)/5xx(서버), 422=검증
- 멱등: GET/PUT/DELETE O, POST/PATCH X

---

## 2-4. Pydantic Settings · 비밀값 관리

### 작동 / 이 프로젝트
- `config.py`의 `Settings(BaseSettings)` — `.env`에서 환경변수를 **타입 검증**하며 로드.
- `get_settings()` + `lru_cache` — 싱글턴처럼 1회 로드.
- **비밀값 규칙(CLAUDE.md)**: DART_API_KEY·LLM_API_KEY는 `.env`에서만, 하드코딩·로깅 금지, `.env` 커밋 금지(`.env.example`만).

### 왜 (12-factor)
- 설정·비밀을 코드에서 분리 → 환경(집/교육센터/CI/배포)마다 다른 값을 코드 변경 없이.

### 면접 Q&A
**Q. 비밀값(API 키)은 어떻게 관리했나요?**
> .env에서만 읽고 코드엔 하드코딩·로깅하지 않았습니다. Pydantic Settings로 타입 검증하며 로드하고, .env는 커밋 금지(.env.example만 저장소에). 12-factor의 "설정은 환경에" 원칙을 따랐습니다.

### 🎴 암기 카드
- BaseSettings = .env → 타입검증 로드
- 비밀: .env만, 하드코딩·로깅·커밋 금지
- 12-factor: 설정은 코드가 아니라 환경에
