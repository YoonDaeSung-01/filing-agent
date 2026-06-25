# 01. Python · 개발 도구 (★★)

> 기본기지만 "왜 이걸 썼나"를 말할 수 있으면 실무 감각으로 읽힌다.

---

## 1-1. Python 3.12

### 한 줄 정의
> AI/데이터 엔지니어링의 사실상 표준 언어. 동적 타입 + 풍부한 ML/LLM 생태계.

### 왜 (이 프로젝트)
- transformers·torch·litellm·sentence-transformers 등 핵심 라이브러리가 전부 Python 우선.
- 빠른 프로토타이핑, 타입 힌트로 안정성 보강.

### 알아둘 포인트
- **타입 힌트** — 런타임에 강제는 안 되지만(주석 수준) IDE·린터·가독성에 큰 도움. `list[str]`, `int | None`(3.10+ union).
- **3.12 변화** — f-string 파싱 개선, 에러 메시지 개선, 성능 향상.
- **GIL(Global Interpreter Lock)** — CPython은 한 번에 한 스레드만 바이트코드 실행 → CPU 바운드는 멀티프로세싱, **I/O 바운드는 async**로 푼다. (LLM·DB 호출은 I/O 바운드 → FastAPI async가 유효)

### 면접 Q&A
**Q. Python GIL이 뭐고 어떤 영향이 있나요?**
> CPython이 한 번에 한 스레드만 실행하게 하는 락입니다. CPU 바운드 작업은 스레드로 병렬화가 안 돼 멀티프로세싱을 쓰고, LLM·DB 호출 같은 I/O 바운드는 async로 동시성을 얻습니다.

### 🎴 암기 카드
- 타입힌트=주석수준(런타임 강제X) but 가독성·도구 이점
- GIL: CPU바운드→멀티프로세스, I/O바운드→async

---

## 1-2. uv (패키지·프로젝트 관리)

### 한 줄 정의
> Rust로 작성된 초고속 Python 패키지/가상환경 관리자(Astral 제작, ruff와 같은 팀).

### 작동 원리 / 구성
- `pyproject.toml` — 프로젝트 메타 + 의존성 **선언**(사람이 읽는 의도).
- `uv.lock` — 의존성의 **정확한 버전·해시 고정**(재현성). 커밋함.
- `.venv` — 가상환경(격리). 커밋 안 함.
- 핵심 명령:
  | 명령 | 의미 |
  |---|---|
  | `uv add <pkg>` | 의존성 추가 + lock 갱신 + 설치 |
  | `uv remove <pkg>` | 제거 |
  | `uv sync` | lock대로 환경 **재현** |
  | `uv run <cmd>` | 가상환경 안에서 실행(활성화 불필요) |

### 왜 (vs pip/poetry)
- 훨씬 빠름(Rust), lock 기반 재현성, 단일 도구로 환경·실행까지.

### 이 프로젝트에서 실제 사용
- 두 노트북(집·교육센터)에서 `uv sync`로 **동일 환경 보장**.
- `uv add psycopg[binary]`, `uv add sentence-transformers` 등으로 의존성 관리.

### 면접 Q&A
**Q. 의존성 관리를 어떻게 했나요?**
> uv로 pyproject.toml에 선언하고 uv.lock으로 버전을 고정했습니다. 다른 PC에서도 uv sync 한 번으로 동일 환경이 재현돼, 두 노트북을 오가는 작업에서 "내 PC에선 됐는데" 문제를 없앴습니다.

### 🎴 암기 카드
- pyproject(선언) + uv.lock(고정) + .venv(격리)
- add/remove/sync/run
- lock 커밋 = 재현성

---

## 1-3. ruff (린터 + 포매터)

### 한 줄 정의
> Rust 기반 초고속 린터/포매터. flake8·isort·black·pyupgrade를 하나로 대체.

### 작동 / 이 프로젝트 설정
- `select = ["E","F","I","UP","B"]`:
  - **E/F** = pycodestyle/pyflakes(스타일·미사용 변수·import)
  - **I** = isort(import 정렬)
  - **UP** = pyupgrade(낡은 문법 현대화)
  - **B** = bugbear(흔한 버그 패턴, 예: `zip(strict=)`)
- `ruff check .`(검사), `ruff check --fix`(자동 수정).
- line-length=100, target py312.

### 실제 겪은 예
- import 정렬(I001), 줄 길이(E501), `zip()`에 `strict=True` 권고(B905), 미사용 import(F401) 등을 커밋 전 `ruff check`로 잡음.

### 면접 Q&A
**Q. 코드 품질은 어떻게 관리했나요?**
> ruff로 린트를 강제했습니다. import 정렬·미사용 변수·낡은 문법·흔한 버그 패턴을 커밋 전에 잡고, Phase 6에서 CI에 넣어 푸시마다 자동 검사할 계획입니다.

### 🎴 암기 카드
- ruff = 린트+포맷, Rust, flake8/isort/black 대체
- E/F/I/UP/B
- check / check --fix

---

## 1-4. pytest (테스트)

### 한 줄 정의
> Python 표준 테스트 프레임워크. `assert` 기반, 픽스처·파라미터화 지원.

### 이 프로젝트의 핵심 원칙 (중요)
> **"키·DB·실제 모델 없이도 통과해야 한다."**
- 네트워크(DART)·pgvector·임베딩·리랭킹은 **모킹/순수함수 분리**로 테스트.
- 부수효과(I/O·모델)를 **순수 함수**와 분리 → 순수 로직만 빠르게 검증.

### 실제 테스트 구성
| 파일 | 검증(키·모델 불필요) |
|---|---|
| `test_chunker.py` | 청킹 경계·overlap·메타데이터 |
| `test_facts.py` | DART 파싱(콤마/CFS/OFS) — 픽스처 |
| `test_reranker.py` | 정렬 로직(`_attach_and_sort`) — 모델 없이 |
| `test_retriever.py` | 토큰화·RRF(`_rrf_fuse`) — DB 없이 |
| `test_ask.py`, `test_health.py` | API |

### 왜 이렇게 (설계 철학)
- CI에서 외부 키·서비스 없이 빠르게 돌아야 함.
- 그래서 "순수 로직 ↔ 부수효과"를 일부러 분리(예: 리랭킹의 정렬만 떼어 테스트).

### 면접 Q&A
**Q. 외부 API·모델에 의존하는 코드를 어떻게 테스트했나요?**
> 부수효과를 순수 함수와 분리했습니다. 예를 들어 리랭킹은 모델 추론과 정렬 로직을 나눠 정렬만 테스트하고, RRF·토큰화는 DB 없이 순수 함수로 검증합니다. DART 응답은 픽스처로 모킹합니다. 덕분에 키·DB·모델 없이 20개 테스트가 다 통과합니다.

### 🎴 암기 카드
- 원칙: 키·DB·모델 없이 통과
- 순수함수 분리 → 빠른 테스트
- 모킹/픽스처로 외부 의존 대체

---

## 1-5. 타입 시스템 — TypedDict · Pydantic

### TypedDict (이 프로젝트의 "구조화 값")
- dict인데 **키와 타입이 정해진** 것. 런타임 오버헤드 없이 타입 체크.
- 이 프로젝트: `FinancialFact`(company·account·year·value·fs_div·source), `Chunk`, `RetrievedChunk`.
- **왜 중요** — "LLM이 숫자를 텍스트로 옮기다 틀리는" 실패를 막으려, 재무 수치를 **타입 있는 값**으로 다룸(plan.md 핵심).

### Pydantic vs TypedDict
| | TypedDict | Pydantic BaseModel |
|---|---|---|
| 런타임 검증 | 안 함(정적 힌트) | **함**(잘못된 타입 거부) |
| 용도 | 내부 구조화 값 | API 입출력·설정 검증 |
| 이 프로젝트 | FinancialFact 등 | AskRequest/Response, Settings |

### 면접 Q&A
**Q. TypedDict와 Pydantic을 어떻게 구분해 썼나요?**
> 내부에서 주고받는 구조화 값(재무 사실·청크)은 런타임 비용 없는 TypedDict로, 외부 경계(API 요청/응답, 환경설정)는 런타임 검증이 필요해 Pydantic으로 썼습니다.

### 🎴 암기 카드
- TypedDict = 정적 힌트(런타임 검증X), 내부 구조화 값
- Pydantic = 런타임 검증, API·설정 경계
- 구조화 값 = LLM 숫자 베끼기 방지
