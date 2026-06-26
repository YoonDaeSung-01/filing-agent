# Phase 6 설계서 — 관측 & 배포 (Langfuse · Docker · GitHub Actions CI)

> 작성일: 2026-06-26 · 상태: **설계 확정 대기(구현 전)**
> 근거: `docs/plan.md` Phase 6. 이 문서는 완성된 에이전트(Phase 1~5) 위에 "관측·컨테이너화·CI"를
> 어떻게 얹을지 먼저 합의하기 위한 것. 검증 후 구현 착수.

## 1. 목표 & 범위

**목표** — "모델을 만든다"에서 "제품으로 운영한다"로 넘어가는 마지막 다리를 놓는다. 한 질문의 전체 실행을
트레이스로 들여다보고(Langfuse), `docker compose up` 한 번으로 앱을 띄우며, 푸시할 때마다 CI가 린트·테스트를
자동 실행한다.

| 들어가는 것 (Phase 6) | 빠지는 것 (스코프 밖) |
|---|---|
| 관측: Langfuse 클라우드 무료 티어 트레이싱(에이전트 그래프 전체) | Langfuse 셀프호스트(부가 서비스 5개+ — 1대 로컬에 과함) |
| 컨테이너화: Dockerfile(앱) + compose에 app 서비스 추가 | Qdrant 전환 실험(plan.md 선택 항목 — 범위 밖) |
| CI: GitHub Actions에서 ruff → pytest 자동 실행 | 라이브 평가(키 필요) CI 게이트 — Phase 5에서 로컬로 결정 |
| README 운영 섹션 갱신(실행법·아키텍처·한계) | 멀티에이전트·MCP 서버화(확장 아이디어) |

> 원칙(CLAUDE.md): **비밀값은 .env에서만 읽고 하드코딩·로깅 금지**, **테스트는 키·DB·모델 없이 통과**.
> Phase 6의 모든 설계는 이 두 줄을 깨지 않는 선에서 관측·배포를 더한다.

---

## 2. 핵심 설계 긴장 (가장 먼저 합의할 것)

### 긴장 ① 관측은 키가 있어야 동작하지만, 원칙은 "키 없이 통과"다

Langfuse 트레이싱은 `LANGFUSE_PUBLIC_KEY`·`LANGFUSE_SECRET_KEY`가 있어야 켜진다. 그런데 이 프로젝트는
키 없이도 앱이 뜨고 테스트가 전부 통과해야 한다(Phase 5와 같은 긴장).

**해결 — 관측은 항상 선택적·부가적(additive)으로 둔다.** 키가 없으면 콜백 핸들러를 만들지 않고 빈 리스트를
반환해 무력화한다(no-op). 키가 있으면 그때만 트레이싱이 붙는다. 그래서:
- 키 없는 CI·로컬에서 앱과 테스트가 그대로 돈다.
- 관측 코드는 순수 함수(키 유무 분기)라 키 없이 단위 테스트할 수 있다.

### 긴장 ② LLM 호출 경로가 두 개라 콜백 하나로 다 못 잡는다

현재 LLM/임베딩 호출은 두 경로로 나간다.

| 경로 | 위치 | 호출 방식 | 무엇을 처리하나 |
|---|---|---|---|
| A | `agent/graph.py` | `ChatLiteLLM`(langchain_litellm) | 에이전트 ReAct 루프·finalize(POST /ask 본류) |
| B | `llm/client.py` | `litellm.completion`/`litellm.embedding` 직접 | 임베딩(retriever), 직접 RAG `ask()` |

LangChain 콜백 핸들러는 경로 A(그래프 전체)를 잡고, LiteLLM 네이티브 콜백은 경로 B를 잡는다. 하나만으로는
반쪽짜리 트레이스가 된다.

**해결 — 두 메커니즘을 함께, 둘 다 키로 게이트한다.**
- **주(主)**: Langfuse **LangChain CallbackHandler**를 `graph.invoke(..., config={"callbacks": [...]})`에 넘긴다.
  → 그래프의 노드·ChatLiteLLM 호출·도구 호출이 한 트레이스로 묶인다(데모 DoD가 요구하는 "한 질문의 전체 트레이스").
- **보조**: 앱 시작 시 `litellm.callbacks = ["langfuse_otel"]`를 한 번 설정한다. → 경로 B의 임베딩·직접 호출도 기록.
  (설치된 langfuse v4는 OTEL-native라, litellm의 v2용 `"langfuse"` 콜백 대신 **`"langfuse_otel"`**를 쓴다.)
- 둘 다 키가 없으면 설정하지 않는다.

> 이 결정이 Phase 6 관측 전체의 토대다. 아래 4장이 여기에 의존한다.

### 긴장 ③ 무거운 ML 의존성(torch)이 이미지·CI를 키운다

리랭커(`BAAI/bge-reranker-v2-m3`)는 `sentence-transformers`→`torch`를 끌어온다(수 GB). 이걸 그대로 이미지에
구우면 이미지가 2~3GB가 되고 CI `uv sync`도 무거워진다. 이건 **결정이 필요한 트레이드오프**다(9장 #4).

---

## 3. 만들 / 수정할 파일

| 파일 | 신규/수정 | 역할 |
|---|---|---|
| `src/filing_agent/observability.py` | 신규 | 키 있을 때만 Langfuse 콜백 생성(없으면 no-op). 순수 분기 |
| `src/filing_agent/config.py` | 수정 | `langfuse_public_key`·`langfuse_secret_key`·`langfuse_host` 추가 |
| `src/filing_agent/api/main.py` | 수정 | 시작 시 LiteLLM 콜백 설정 + `graph.invoke`에 콜백 핸들러 전달 |
| `tests/test_observability.py` | 신규 | 키 없으면 빈 콜백(no-op), 키 있으면 핸들러 생성(모킹) |
| `Dockerfile` | 신규 | uv 기반 멀티스테이지 — 앱 이미지화 |
| `.dockerignore` | 신규 | `.venv`·`data/`·`.git`·캐시 제외(빌드 컨텍스트 축소) |
| `docker-compose.yml` | 수정 | 기존 pgvector에 `app` 서비스 추가(pgvector healthy 후 기동) |
| `.env.example` | 수정 | Langfuse 3개 키 항목 추가(주석) |
| `.github/workflows/ci.yml` | 신규 | push·PR에서 ruff → pytest 자동 실행(키 불필요) |
| `pyproject.toml` | 수정 | `uv add langfuse`(런타임 의존성 추가) |
| `README.md` | 수정 | 운영 섹션(실행법·아키텍처·한계) 현행화 |
| `CLAUDE.md` | 수정 | "현재 상태" 줄 Phase 6 완료로 갱신 |

---

## 4. 관측 (observability.py)

키 유무로 분기하는 얇은 모듈 하나로 둔다. `logging_config.py`와 같은 위상(앱 전역 설정 헬퍼)이다.

### 4.1 설계 원칙
- **선택적**: 키 없으면 `[]` 반환 → 호출부는 분기 없이 그대로 `config={"callbacks": []}`를 넘기면 된다.
- **지연 임포트**: `langfuse`는 키가 있을 때만 import → 의존성 미설치·키 없는 환경에서도 모듈 임포트가 안 깨진다.
- **비밀값**: 키는 `Settings`(=.env)에서만 읽는다. 로깅하지 않는다.

### 4.2 ⚠️ 키 전파 — 자체 검토에서 발견한 간극

**문제**: `pydantic-settings`는 `.env`를 **`Settings` 객체로만** 읽고 `os.environ`에는 넣지 않는다
(현재 코드에 `load_dotenv`·`os.environ` 사용이 전혀 없음). 그런데 Langfuse SDK의 `CallbackHandler()`와
LiteLLM의 langfuse 콜백은 **`os.environ`에서** `LANGFUSE_*` 키를 읽는다. 키를 `.env`에만 두면 핸들러가 키를
못 찾아 **트레이싱이 조용히 안 켜진다**(에러도 없이 무음 실패 — 가장 디버깅하기 나쁜 형태).

**해결**: 관측 활성화 시 `Settings`의 키를 **`os.environ`으로 한 번 전파**한다. Settings(=.env)에서 읽어
런타임 프로세스 환경에만 복사하므로 "비밀값은 .env에서만, 하드코딩·로깅 금지" 원칙을 깨지 않는다.

### 4.3 인터페이스(안)
먼저 의도: `configure_observability()`가 진입점이다 — 키가 있으면 (1) `os.environ`에 전파하고
(2) LiteLLM 콜백을 등록한다(경로 B). `get_langfuse_callbacks()`는 그래프 호출(경로 A)에 끼울 핸들러를 준다.

```python
def _enabled(cfg) -> bool:
    """Langfuse 공개·비밀 키가 둘 다 있으면 True."""
    return bool(cfg.langfuse_public_key and cfg.langfuse_secret_key)

def configure_observability() -> None:
    """앱 시작 시 1회. 키 있을 때만 환경 전파 + LiteLLM 콜백 등록(멱등)."""
    cfg = get_settings()
    if not _enabled(cfg):
        return
    import os
    # .env→Settings→os.environ 전파(Langfuse/LiteLLM이 환경변수에서 읽음)
    os.environ.setdefault("LANGFUSE_PUBLIC_KEY", cfg.langfuse_public_key)
    os.environ.setdefault("LANGFUSE_SECRET_KEY", cfg.langfuse_secret_key)
    os.environ.setdefault("LANGFUSE_HOST", cfg.langfuse_host)
    import litellm
    if "langfuse_otel" not in (litellm.callbacks or []):
        litellm.callbacks = [*(litellm.callbacks or []), "langfuse_otel"]

def get_langfuse_callbacks() -> list:
    """그래프 invoke에 넘길 콜백 핸들러 리스트. 키 없으면 [] (no-op)."""
    cfg = get_settings()
    if not _enabled(cfg):
        return []
    from langfuse.langchain import CallbackHandler  # 지연 임포트(키 있을 때만)
    return [CallbackHandler()]  # 4.2 전파 덕에 os.environ에서 키를 찾음
```

> ✅ **버전 확인 완료**: 설치된 **langfuse 4.12.0** 기준 — import 경로는 `from langfuse.langchain import
> CallbackHandler`(v4 확인), `CallbackHandler()`는 전역 클라이언트가 `os.environ`의 `LANGFUSE_*`를 읽는다.
> litellm의 직접 호출 경로는 langfuse v2 API를 쓰는 `"langfuse"`가 v4와 깨지므로 **OTEL 기반 `"langfuse_otel"`**를
> 쓴다(`os.environ`만 읽어 v4 호환).

### 4.4 호출부 (api/main.py)
- 모듈 로드 시 `configure_observability()`를 `configure_logging()` 옆에서 호출(키 없으면 no-op).
- `POST /ask`에서 `graph.invoke(initial, config={"callbacks": get_langfuse_callbacks()})`로 핸들러 전달.
- 키가 없으면 둘 다 no-op이라 동작·성능 변화 없음.

---

## 5. 컨테이너화 (Dockerfile · compose)

목표: `docker compose up` 한 번에 앱 + pgvector가 뜬다. Langfuse는 클라우드라 compose에 넣지 않는다.

### 5.1 Dockerfile (uv 멀티스테이지)
먼저 의도: 빌드 단계에서 의존성을 설치해 레이어 캐시를 살리고, 실행 단계는 가볍게 유지한다.

```dockerfile
FROM python:3.12-slim AS base
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /app

# 의존성 레이어(소스보다 먼저 — 캐시 적중률↑)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# 앱 소스
COPY src/ ./src/
RUN uv sync --frozen --no-dev

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "filing_agent.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 5.2 compose에 app 추가 (기존 pgvector 유지)
```yaml
services:
  pgvector:
    # ... (기존 그대로) ...
  app:
    build: .
    ports:
      - "8000:8000"
    env_file: .env
    environment:
      # 컨테이너 내부에서 DB는 서비스명으로 접근(localhost 아님)
      PG_DSN: postgresql://filing:filing@pgvector:5432/filing_agent
    depends_on:
      pgvector:
        condition: service_healthy
```

- ⚠️ **DSN 호스트 차이**: 로컬은 `localhost:5433`, 컨테이너 내부는 `pgvector:5432`. compose의
  `environment`로 덮어써 해결한다.
- `.dockerignore`로 `.venv`·`data/`·`.git`·`.pytest_cache`·`.ruff_cache`를 빌드 컨텍스트에서 제외.

### 5.3 이미지 무게 (긴장 ③ 연결)
리랭커(torch)를 포함하면 이미지가 커진다. 9장 #4의 결정에 따라 (A) 전체 포함 또는 (B) 의존성 분리 중 하나를
택한다. 결정 전까지 Dockerfile은 전체 의존성 기준으로 둔다.

---

## 6. CI (.github/workflows/ci.yml)

목표: 푸시·PR마다 린트와 테스트가 자동으로 돈다. **키·DB가 필요 없다** — Phase 1~5가 모든 외부 호출을
픽스처·모킹으로 분리해 둔 덕분이다.

```yaml
name: CI
on:
  push: { branches: [main] }
  pull_request: { branches: [main] }
jobs:
  lint-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with: { enable-cache: true }
      - run: uv sync --frozen
      - run: uv run ruff check
      - run: uv run pytest
```

- **"eval 스모크"의 정체**: plan.md는 CI에 평가 스모크를 넣자고 했지만, Phase 5에서 **라이브 평가는 로컬,
  CI는 결정론 회귀(채점 로직 + 모킹 도구 슬라이스)만**으로 확정했다. 그 회귀 테스트는 이미 `pytest`에
  포함돼 있으므로 별도 스텝이 필요 없다(`uv run pytest` 한 줄로 커버).
- **pgvector 불필요**: 테스트가 DB를 모킹하므로 CI에 서비스 컨테이너를 띄우지 않는다.
- **torch 무게**: `enable-cache`로 uv 캐시를 재사용해 완화. 9장 #4에서 의존성을 분리하면 더 가벼워진다.

---

## 7. 보안 점검 (.env·키)

- `.env`는 이미 `.gitignore`에 있음 → 커밋되지 않음. Langfuse 키도 `.env`에만 둔다.
- `.env.example`에는 **빈 키 항목 + 주석**만 추가(값 없음).
- 관측 코드·로그 어디에도 키 문자열을 출력하지 않는다(Langfuse SDK가 환경변수에서 직접 읽음).
- compose의 `app` 서비스는 `env_file: .env`로 키를 주입 → 이미지에 키를 굽지 않는다.

---

## 8. config / .env.example 추가 항목

```python
# config.py (Settings에 추가)
langfuse_public_key: str = ""
langfuse_secret_key: str = ""
langfuse_host: str = "https://cloud.langfuse.com"  # 클라우드 무료 티어 기본값
```

```bash
# .env.example (주석으로 추가)
# ── 관측 (Phase 6, 선택) ──────────────────────────────────────
# LANGFUSE_PUBLIC_KEY=    # 없으면 트레이싱 비활성(앱은 정상 동작)
# LANGFUSE_SECRET_KEY=
# LANGFUSE_HOST=https://cloud.langfuse.com
```

---

## 9. 결정 사항

1. **Langfuse 배포 형태** — ✅ **클라우드 무료 티어**. 셀프호스트는 Postgres 등 부가 서비스가 많아 1대
   로컬에 과하다(plan.md 일치).
2. **트레이싱 메커니즘** — ✅ **LangChain CallbackHandler(주, 그래프 전체) + LiteLLM 네이티브 콜백(보조,
   직접 호출)**. 둘 다 키로 게이트(2장 긴장 ②).
3. **관측 활성화 방식** — ✅ **선택적·부가적(키 없으면 no-op)**. 키 없는 테스트·CI 통과 보장(2장 긴장 ①).
4. **Docker/CI 의존성 무게** — ✅ **(A) 전체 포함**(torch까지 한 이미지) + uv 캐시. 자체 완결·구성 단순.
   plan.md "실무 스택을 직접 경험" 취지에 부합하고, 분리(B)는 정제 늪 리스크. 이미지 크기(2~3GB)
   트레이드오프는 README 한계에 명시. (두 노트북 워크플로와는 무관 — 이미지는 노트북별 로컬 빌드물)
5. **CI 범위** — ✅ **ruff + pytest만(키 없이)**. 라이브 평가는 로컬(Phase 5 확정). 별도 eval 스텝 없음.
6. **Qdrant 전환 실험** — ✅ **범위 밖**. plan.md의 선택 항목, 확장으로 미룸.

---

## 10. 작업 순서 (각 단계 ruff·pytest → 커밋)

1. `uv add langfuse` → `config.py`에 키 3개 추가 → `.env.example` 갱신.
2. `observability.py`(키 분기) + `tests/test_observability.py`(키 없으면 `[]`, 키 모킹 시 핸들러).
3. `api/main.py` 배선(`configure_observability()` + `graph.invoke`에 콜백). 키 없이 회귀 확인.
4. `Dockerfile` + `.dockerignore` + `docker-compose.yml`에 app 서비스. 로컬 `docker compose up` 수동 확인.
5. `.github/workflows/ci.yml` 추가 → 푸시해 Actions 녹색 확인.
6. `README.md` 운영 섹션 현행화(실행법·아키텍처·평가표 자리·한계) + `CLAUDE.md` 상태 갱신 + 커밋.

> (선택, 키 보유 시) Langfuse 클라우드에 한 질문을 보내 전체 트레이스가 한 화면에 뜨는지 수동 확인.

---

## 11. 완료 기준 (DoD)

- `docker compose up` 한 번으로 앱(+pgvector)이 뜬다.
- 푸시하면 GitHub Actions가 ruff·pytest를 자동 실행하고 통과한다(키 없이).
- 관측 코드가 **키 없이 통과**한다(키 없으면 no-op, 있으면 핸들러 생성 — 단위 테스트로 검증).
- (키 보유 시) Langfuse 클라우드에서 한 질문의 **전체 트레이스**(그래프 노드·LLM·도구)를 열어볼 수 있다.
- 비밀값이 코드·로그·이미지·저장소 어디에도 노출되지 않는다(.env 전용).
- README가 현재 기능(에이전트·하이브리드 검색·하네스·평가)과 실행법을 반영한다.
