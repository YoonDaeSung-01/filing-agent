# 기술 스택 가이드 — filing-agent에서 쓴 것 + IT 업계 단골 기술

> 목적: 이 프로젝트를 진행하며 실제로 쓴 기술을 **"무엇·왜·대안·면접 한 줄"** 형식으로 정리하고,
> AI/백엔드 엔지니어 면접에서 자주 나오는 주변 기술까지 한 번에 훑는 학습용 문서.
> 작성일: 2026-06-26 (Phase 2까지 반영)

---

## Part 1. 이 프로젝트에서 실제로 쓴 기술

### A. 언어 · 개발 환경

#### Python 3.12
- **무엇** — AI/데이터 엔지니어링의 사실상 표준 언어.
- **왜** — 풍부한 ML/LLM 생태계(transformers·torch·litellm), 빠른 프로토타이핑.
- **3.12 포인트** — 타입 힌트 개선, f-string 파싱 개선, 성능 향상.
- **면접 한 줄** — "타입 힌트 + TypedDict로 구조화 값을 다뤄 런타임 오류를 줄였다."

#### uv (패키지·프로젝트 관리)
- **무엇** — Rust로 작성된 초고속 Python 패키지/가상환경 관리자(Astral 제작).
- **왜** — pip/poetry보다 빠르고, `pyproject.toml` + `uv.lock`으로 **재현 가능한** 환경.
- **핵심 명령** — `uv add <pkg>`(의존성 추가), `uv sync`(lock대로 설치), `uv run <cmd>`(가상환경에서 실행).
- **대안** — pip+venv, poetry, pipenv, conda.
- **면접 한 줄** — "uv.lock으로 두 노트북에서 동일 환경을 보장했다(재현성)."

#### ruff (린터 + 포매터)
- **무엇** — Rust 기반 초고속 린터/포매터. flake8·isort·black·pyupgrade를 하나로 대체.
- **왜** — 빠르고 설정 단순, CI에서 코드 품질 게이트.
- **이 프로젝트 설정** — `select = ["E","F","I","UP","B"]` (pycodestyle/pyflakes/isort/pyupgrade/bugbear).
- **면접 한 줄** — "초기부터 린트를 강제해 일관된 코드 스타일과 import 정렬을 유지했다."

#### pytest (테스트)
- **무엇** — Python 표준 테스트 프레임워크.
- **이 프로젝트 원칙** — "키·DB·실제 모델 없이도 통과." 네트워크·pgvector·임베딩·리랭킹은 **모킹/순수함수 분리**로 테스트.
- **왜 중요** — CI에서 외부 의존 없이 빠르게 돌아야 함. 순수 로직(청킹·RRF·정렬)을 따로 떼어 테스트 가능하게 설계.
- **면접 한 줄** — "부수효과(I/O·모델)를 순수함수와 분리해 테스트 가능성을 확보했다."

#### Git / GitHub
- **무엇** — 분산 버전관리 + 원격 협업 플랫폼.
- **이 프로젝트 활용** — 두 노트북(집·교육센터)의 **sync 수단**. Phase 단위로 의미 있는 커밋.
- **면접 한 줄** — "Phase별로 동작하는 상태를 커밋해 항상 롤백 가능한 지점을 유지했다."

---

### B. 웹 API 계층

#### FastAPI
- **무엇** — Python 비동기 웹 프레임워크. Starlette(ASGI) + Pydantic 기반.
- **왜** — 타입 힌트로 **자동 검증 + 자동 OpenAPI 문서(`/docs`)**, 비동기 지원, 빠름.
- **이 프로젝트** — `GET /health`, `GET /ask`(템플릿), `POST /ask`(RAG/에이전트). 요청·응답을 Pydantic 모델로.
- **대안** — Flask(동기·미니멀), Django(풀스택), Express(Node).
- **면접 한 줄** — "Pydantic 모델로 입출력 스키마를 강제하고 자동 문서를 얻었다."

#### uvicorn (ASGI 서버)
- **무엇** — FastAPI 앱을 실제로 구동하는 ASGI 서버.
- **WSGI vs ASGI** — WSGI(동기, Flask/Django 전통)와 달리 ASGI는 **비동기** I/O 지원 → 동시성에 유리.
- **면접 한 줄** — "ASGI라 I/O 바운드(LLM·DB 호출)에서 동시성 이점이 있다."

#### Pydantic / pydantic-settings
- **무엇** — 데이터 검증 + 설정 관리 라이브러리.
- **이 프로젝트** — `Settings(BaseSettings)`로 `.env`에서 비밀키·설정을 타입 검증해 로드.
- **왜** — 비밀값을 코드와 분리(`.env`만, 커밋 금지), 잘못된 타입을 시작 시점에 차단.
- **면접 한 줄** — "설정·비밀값을 코드에서 분리하고 타입으로 검증했다(12-factor)."

---

### C. 데이터 수집 계층

#### OpenDART API (데이터 소스)
- **무엇** — 한국 금융감독원 전자공시 시스템의 공개 API(무료 인증키).
- **이 프로젝트 주의점** —
  - `corp_code`(8자리 고유번호) ≠ 종목코드 → `corpCode.xml`(zip)로 매핑.
  - 실패도 **HTTP 200 + 본문 `status`**로 알림 → `status != "000"` 처리 필수.
  - 금액은 콤마 문자열(`"300,870,903"`) → 콤마 제거 후 int.
  - 연결(CFS) 없으면 별도(OFS)로 폴백.
- **면접 한 줄** — "외부 API의 비표준 에러 규약(200+status)과 한국 회계 특성(CFS/OFS)을 방어적으로 처리했다."

#### httpx (HTTP 클라이언트)
- **무엇** — requests의 현대적 후계자. 동기/비동기 모두 지원.
- **면접 한 줄** — "타임아웃·재시도·요청 지연으로 외부 API 호출을 견고하게 만들었다."

#### BeautifulSoup + lxml (HTML/XML 파싱)
- **무엇** — BeautifulSoup은 파싱 인터페이스, lxml은 빠른 파서 백엔드.
- **이 프로젝트** — 사업보고서 원문(document.xml ZIP)에서 가장 큰 HTML을 골라 순수 텍스트 추출.
- **면접 한 줄** — "공시 원문에서 서술 섹션 텍스트만 추출해 RAG 코퍼스를 만들었다."

#### 캐싱 (직접 구현)
- **무엇** — 외부 API 응답을 디스크에 저장하고, 있으면 네트워크를 건너뜀.
- **왜** — DART는 **키당 일일 호출 한도**가 있음 → 같은 데이터 재요청 금지.
- **면접 한 줄** — "API 한도를 고려해 응답을 캐싱하고 status가 정상일 때만 영구 저장했다."

---

### D. RAG / 검색 계층 (이 프로젝트의 핵심)

#### 임베딩 (Embedding)
- **무엇** — 텍스트를 의미를 담은 고정 길이 벡터로 변환. 의미가 비슷하면 벡터도 가까움.
- **이 프로젝트** — OpenAI `text-embedding-3-small`(1536차원). 호스팅 API로 로컬 CPU 부담 0.
- **대안** — BGE-M3(다국어·로컬·MIT), Cohere embed, OpenAI 3-large.
- **면접 한 줄** — "한국어 공시라 다국어 임베딩이 필요했고, CPU 부담을 줄이려 임베딩만 호스팅 API로 뺐다(트레이드오프)."

#### pgvector (벡터 DB)
- **무엇** — PostgreSQL의 벡터 검색 확장. `vector` 타입 + 거리 연산자 + ANN 인덱스.
- **거리 연산자** — `<=>`(코사인), `<->`(L2/유클리드), `<#>`(내적).
- **왜 선택** — 별도 벡터 DB 없이 **Postgres 하나로** 관계형 + 벡터를 함께(운영 단순). 2026 RAG 기본값 중 하나.
- **대안** — Qdrant(필터 강함), Weaviate, Milvus, Pinecone(매니지드), Chroma(프로토타입).
- **면접 한 줄** — "메타데이터 필터와 벡터 검색을 한 DB에서 처리하려 pgvector를 택했다."

#### HNSW 인덱스
- **무엇** — Hierarchical Navigable Small World. 그래프 기반 **근사 최근접 이웃(ANN)** 알고리즘.
- **왜** — 정확 검색(brute force)은 O(n)이라 느림 → HNSW로 **속도/재현율 균형**.
- **IVFFlat과 비교** — HNSW는 빌드 시 학습 데이터 불필요(동적 삽입에 유리), 메모리는 더 씀. IVFFlat은 클러스터 학습 필요.
- **면접 한 줄** — "동적 인덱싱에 유리한 HNSW로 ANN 검색을 구성했다."

#### 청킹 (Chunking)
- **무엇** — 긴 문서를 검색 단위로 쪼개기. 임베딩·LLM 컨텍스트 한계 때문에 필요.
- **이 프로젝트 진화** — Phase 1 고정 크기+overlap → Phase 2 **문단/문장 경계 존중**(문장 중간 절단 방지).
- **트레이드오프** — 너무 크면 정밀도↓(관련 없는 내용 섞임), 너무 작으면 문맥 단절. overlap으로 경계 문맥 보존.
- **면접 한 줄** — "고정 분할이 문장을 끊는 문제를 문단→문장 경계 존중으로 개선했다."

#### BM25 (희소/키워드 검색)
- **무엇** — 전통적 키워드 랭킹. 단어 빈도(TF) × 역문서빈도(IDF) + 문서 길이 정규화.
- **왜 RAG에 추가** — 임베딩(의미)은 **정확한 단어 일치**(회사명·숫자·코드)에 약함. BM25가 이를 보완.
- **이 프로젝트** — `rank-bm25`(Okapi BM25)로 메모리 인덱스, 한글/영숫자 토큰화.
- **면접 한 줄** — "공시엔 회사명·숫자가 많아 의미 검색만으론 부족 → BM25를 결합했다."

#### 하이브리드 검색 + RRF
- **무엇** — 벡터(dense) + BM25(sparse) 결과를 **융합**.
- **RRF (Reciprocal Rank Fusion)** — `score(d) = Σ 1/(k+rank)` (k≈60). **점수 정규화 불필요**, 순위만 사용해 robust.
- **왜 RRF** — 코사인 점수와 BM25 점수는 스케일이 달라 직접 합산 어려움 → 순위 기반 융합이 깔끔.
- **면접 한 줄** — "스케일이 다른 두 랭킹을 RRF로 융합해 정규화 없이 안정적으로 합쳤다."

#### 리랭킹 (Reranking) — bi-encoder vs cross-encoder
- **무엇** — 1차 검색이 가져온 top-N 후보를 더 정밀한 모델로 재정렬해 top-K만 LLM에 전달.
- **bi-encoder(임베딩)** — 질문·문서를 **따로** 인코딩 → 코사인. 빠르고 미리 계산 가능, 정밀도 낮음.
- **cross-encoder(리랭커)** — (질문, 문서)를 **함께** 인코딩 → 관련도 직접 점수화. 느리지만 정밀. 소수 후보에만 사용.
- **이 프로젝트** — `BAAI/bge-reranker-v2-m3`(다국어) via sentence-transformers. top-20 → top-5.
- **함정 메모** — FlagEmbedding의 FlagReranker가 transformers 5.x와 비호환(`prepare_for_model` 제거) → sentence-transformers CrossEncoder로 교체.
- **면접 한 줄** — "재현율 좋은 1차 검색 위에 정밀한 cross-encoder 리랭킹을 얹는 2단계 검색을 구성했다."

#### LiteLLM (LLM 게이트웨이)
- **무엇** — 100+ LLM 공급자(OpenAI·Anthropic·...)를 **하나의 OpenAI 호환 인터페이스**로 추상화.
- **왜** — 공급자 교체를 코드 수정 없이 `.env`의 모델명만으로. 직접 SDK 호출 대신 단일 진입점.
- **이 프로젝트** — `litellm.completion`(답변), `litellm.embedding`(임베딩) 둘 다 경유.
- **면접 한 줄** — "LLM 호출을 게이트웨이로 추상화해 공급자 종속을 줄였다."

---

### E. 인프라 계층

#### Docker / Docker Compose
- **무엇** — 컨테이너(앱+의존성을 격리 패키징) / 멀티 컨테이너 선언적 실행.
- **이 프로젝트** — `docker-compose.yml`로 pgvector(Postgres) 컨테이너를 한 줄(`docker compose up`)로 구동.
- **겪은 함정** — 호스트에 PostgreSQL이 5432 선점 → 컨테이너를 **5433:5432**로 매핑해 회피.
- **면접 한 줄** — "`docker compose up` 한 줄로 의존 서비스를 재현 가능하게 띄웠다."

#### WSL2 (Windows Subsystem for Linux)
- **무엇** — Windows에서 실제 Linux 커널을 돌리는 계층. Docker Desktop의 백엔드.
- **겪은 함정** — 미설치 시 Docker가 "Virtualization not detected" → `wsl --install` + 재시작.
- **면접 한 줄** — "Windows 개발 환경에서 WSL2 기반으로 Linux 컨테이너를 구동했다."

#### psycopg (v3) — Postgres 드라이버
- **무엇** — Python ↔ PostgreSQL 연결 드라이버.
- **왜 v3로 갈아탐** — v2(psycopg2)가 **Windows 한국어 locale에서 libpq 에러 메시지를 cp949로 받아** UTF-8 디코딩 실패(UnicodeDecodeError) → 진짜 에러(인증 실패)가 가려짐. v3는 인코딩을 올바르게 처리.
- **면접 한 줄** — "드라이버의 인코딩 처리 차이로 인한 디버깅 난항을 v3 전환으로 해결했다."

#### PostgreSQL
- **무엇** — 오픈소스 관계형 DB. 확장(pgvector 등) 생태계가 강함.
- **면접 한 줄** — "관계형 + 벡터를 한 DB에서 다루는 Postgres 중심 설계."

---

### F. ML 런타임 (리랭커가 끌고 온 의존성)

| 패키지 | 무엇 | 비고 |
|---|---|---|
| **torch** | 딥러닝 텐서/자동미분 프레임워크 | 리랭커 모델 추론 엔진. CPU 버전(~200MB+) |
| **transformers** | HuggingFace 사전학습 모델 로딩/추론 | 토크나이저·모델 아키텍처 |
| **sentence-transformers** | 임베딩/CrossEncoder 고수준 래퍼 | 리랭킹에 사용 |
| **numpy** | 수치 배열 연산 | 벡터 변환, argsort 등 |

- **메모 ** — "추론만 쓰고 학습(파인튜닝)은 안 함" → "ML 안 하기" 원칙과 충돌 안 함. 모델은 첫 호출 시 1회 다운로드(~600MB) 후 캐시.

---

## Part 2. 코드 너머의 핵심 개념 (면접 단골)

### RAG (Retrieval-Augmented Generation)
- LLM에게 **외부 근거를 검색해 함께 주고** 답하게 하는 패턴("오픈북 시험").
- 파인튜닝 대비 장점: 최신·사실 정보 반영, 비용↓, 출처 제시로 환각 억제.
- 구성: 인제스트(청킹·임베딩·저장) → 검색(벡터/하이브리드/리랭킹) → 생성(컨텍스트+프롬프트).

### 에이전트 / ReAct / Tool Calling (Phase 3 예정)
- **에이전트** — 답을 바로 뱉지 않고 **도구를 골라 쓰고 여러 단계**를 거치는 LLM 시스템.
- **ReAct** — Reasoning + Acting. "추론 → 행동(도구) → 관찰 → 다시 추론" 순환.
- **Tool/Function Calling** — LLM이 정해진 스키마로 함수 호출을 요청 → 시스템이 실행 → 결과를 다시 LLM에.
- **챗봇 vs 에이전트** — 챗봇은 단일 응답, 에이전트는 **도구 라우팅 + 다단계**. (이 프로젝트의 차별화 지점)

### 구조화 출력 (Typed/Structured values)
- LLM이 글에서 숫자를 **눈으로 베끼다 틀리는** 실패를 막기 위해, 수치는 도구가 `{값, 단위, 출처}` 타입으로 반환.
- 위험한 계산(증감률)은 **도구 내부**에서 해 LLM은 식별자만 전달.

### LLMOps / 평가 / 관측 (Phase 5~6 예정)
- **평가(Eval)** — "바꿨더니 좋아졌나?"를 숫자로. Hit@k·MRR(검색), routing accuracy(도구선택), 숫자 정답률(결정론 대조), faithfulness(RAGAS/DeepEval).
- **관측(Observability)** — 각 LLM/도구 호출의 비용·지연·실패를 추적(Langfuse). 트레이스 단위로 디버깅.
- **회귀 테스트** — 골든셋 점수가 기준선 밑으로 떨어지면 CI 실패.

---

## Part 3. 프로젝트엔 아직 없지만 IT 업계에서 자주 쓰는 것

> 면접에서 "이건 안 써봤지만 안다" 수준으로 말할 수 있게 정리.

### 컨테이너 오케스트레이션
- **Kubernetes(K8s)** — 다수 컨테이너의 배포·스케일·복구를 자동화. 대규모 운영의 표준.
- Docker Compose(단일 호스트) ↔ K8s(클러스터) 의 차이.

### CI/CD
- **GitHub Actions**(이 프로젝트 Phase 6 예정), GitLab CI, Jenkins, CircleCI.
- 푸시마다 lint → test → build → deploy 자동화.

### 클라우드
- **AWS**(EC2·S3·Lambda·RDS), GCP, Azure. 매니지드 서비스로 인프라 부담↓.

### IaC (Infrastructure as Code)
- **Terraform**, Pulumi, CloudFormation. 인프라를 코드로 선언·버전관리.

### 데이터/메시징
- **Redis** — 인메모리 캐시/큐/세션 스토어.
- **Kafka / RabbitMQ** — 비동기 메시지 큐, 이벤트 스트리밍.
- **Airflow / Dagster** — 데이터 파이프라인 오케스트레이션.

### 관측 스택
- **Prometheus + Grafana** — 메트릭 수집·시각화.
- **OpenTelemetry(OTEL)** — 트레이싱 표준(Langfuse도 OTEL 호환).
- **ELK(Elasticsearch·Logstash·Kibana)** — 로그 수집·검색.

### 벡터 DB 생태계 (pgvector 외)
- **Pinecone**(매니지드·간편), **Qdrant**(필터·Rust), **Weaviate**, **Milvus**(대규모), **Chroma**(프로토타입).

### LLM/에이전트 프레임워크
- **LangChain**(체인·도구), **LangGraph**(그래프 상태머신·이 프로젝트 Phase 3), **LlamaIndex**(RAG 특화), **DSPy**(프롬프트 최적화).
- **MCP(Model Context Protocol)** — 도구·데이터를 표준 규격으로 LLM에 노출(2026 트렌드).

### API 스타일
- **REST**(이 프로젝트), **GraphQL**(클라이언트가 필요한 필드만), **gRPC**(고성능·바이너리·마이크로서비스 간).

### 인증/보안
- **OAuth2 / OIDC** — 위임 인증.
- **JWT** — 무상태 토큰.
- **프롬프트 인젝션 방어 / 가드레일** — LLM 보안(이 프로젝트 Phase 4 예정).

---

## 한눈에 보는 "이 프로젝트 → 채용 키워드" 매핑

| 구현한 것 | 채용 키워드 |
|---|---|
| 공시 인제스트 + 임베딩 + pgvector 검색 | RAG, 임베딩, 벡터 DB |
| 경계 청킹 + 하이브리드 + 리랭킹 | RAG 고도화, 하이브리드 검색, cross-encoder |
| (예정) 도구 라우팅 에이전트 | LangGraph, ReAct, 에이전틱 AI |
| 재무 수치 구조화 조회 + 도구 내 계산 | 정형/비정형 데이터 통합 |
| (예정) 검증 루프 + 가드레일 | 하네스/루프 엔지니어링, LLM 보안 |
| (예정) 골든셋 + 회귀 테스트 | LLM 평가, LLMOps |
| LiteLLM 게이트웨이 | 멀티 프로바이더 추상화 |
| Docker + (예정)CI | 컨테이너화, CI/CD |

---

*이 문서는 학습·면접 준비용 살아있는 문서다. 새 기술을 도입하면 Part 1에, 개념을 새로 익히면 Part 2/3에 추가한다.*
