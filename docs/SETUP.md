# SETUP.md — 새 노트북 환경 세팅 가이드

> 다른 노트북(교육센터 PC 등)에서 처음부터 따라 하면 동작하는 상태가 되는 체크리스트.
> 기준 OS: **Windows 11**, 셸: **PowerShell**. GitHub 저장소를 sync 수단으로 쓴다.

이 프로젝트는 두 노트북(집·교육센터)을 GitHub로 오가며 작업한다.
**코드·설정은 git에 있지만, 아래 3가지는 git에 없으니 노트북마다 직접 준비해야 한다:**
1. 시스템 도구 (Python·uv·Docker·Git)
2. `.env` (비밀키 — 절대 커밋 안 함)
3. 적재된 데이터 (pgvector DB 내용 — `docker compose up` + `ingest_all.py`로 재생성)

---

## 0. 사전 준비물 (시스템 도구)

| 도구 | 확인 명령 | 없으면 |
|---|---|---|
| Python 3.12 | `python --version` | python.org에서 3.12 설치 |
| uv (패키지 관리) | `uv --version` | 아래 (A) 참고 |
| Git | `git --version` | git-scm.com |
| Docker Desktop | `docker --version` | 아래 (B) 참고 |

### (A) uv 설치 + PATH
```powershell
# 설치 (공식 스크립트)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```
설치 후 `uv`가 안 잡히면 PATH 문제다. uv는 보통 `C:\Users\<사용자>\.local\bin`에 깔린다.
- **임시(현재 세션만):** `$env:Path = "C:\Users\$env:USERNAME\.local\bin;$env:Path"`
- **영구:** 시스템 환경변수 PATH에 `C:\Users\<사용자>\.local\bin` 추가 후 터미널 재시작.

### (B) Docker Desktop + WSL2
Docker Desktop은 **WSL2**가 있어야 컨테이너를 띄운다.
1. Docker Desktop 설치 (docker.com).
2. WSL2 미설치 시 **관리자 권한 PowerShell**에서:
   ```powershell
   wsl --install --no-distribution
   ```
3. **재시작.** (BIOS 가상화(Virtualization)는 보통 기본 ON. "Virtualization support not detected"가 뜨면 BIOS에서 확인)
4. Docker Desktop 실행 → 트레이의 고래🐋 아이콘이 멈추면 준비 완료. **첫 실행은 2~5분 걸린다.**
5. Docker 명령이 안 잡히면 PATH에 `C:\Program Files\Docker\Docker\resources\bin` 추가.

---

## 1. 저장소 클론 + 의존성 설치
```powershell
git clone https://github.com/YoonDaeSung-01/filing-agent.git
cd filing-agent
uv sync                # pyproject.toml 기준 가상환경·의존성 일괄 설치
```
> ⚠️ **무거운 의존성 주의:** 리랭커(sentence-transformers)가 **torch 등 ~2GB**를 받는다.
> 네트워크에 따라 `uv sync`가 수 분 걸릴 수 있다. 정상이다.

---

## 2. `.env` 준비 (비밀키 — git에 없음)
저장소의 `.env.example`을 복사해 `.env`를 만들고 키 2개를 채운다.
```powershell
Copy-Item .env.example .env
```
`.env`에 최소 다음 2개 필수:
```bash
DART_API_KEY=발급받은_DART_키      # opendart.fss.or.kr 무료 발급
LLM_API_KEY=sk-...                 # OpenAI 키 (임베딩+LLM 둘 다 사용)
```
> 🔐 `.env`는 **절대 커밋 금지**. 두 노트북에 각각 직접 넣는다. (git엔 `.env.example`만)

---

## 3. pgvector 띄우기 (Docker)
```powershell
docker compose up -d           # pgvector 컨테이너 백그라운드 실행
docker ps                      # STATUS가 (healthy)인지 확인
```

> ⚠️ **포트 5432 충돌 주의 (집 노트북에서 겪은 문제):**
> Windows에 PostgreSQL이 따로 깔려 있으면(`postgresql-x64-16` 같은 서비스) 5432를 선점한다.
> 그래서 이 프로젝트는 **호스트 포트 5433**으로 고정했다 (`docker-compose.yml`의 `5433:5432`,
> `config.py`의 `pg_dsn` 기본값도 5433). 어느 노트북이든 5433을 쓰므로 추가 설정 불필요.
> 혹시 5433도 충돌하면 `netstat -ano | findstr :5433`로 확인.

---

## 4. 데이터 적재 (pgvector 채우기)
```powershell
uv run python scripts/ingest_all.py
```
- DART에서 재무 수치·사업보고서 텍스트를 받아(캐시 있으면 재사용) 청킹→임베딩→pgvector 저장.
- 처음엔 DART 호출 + 임베딩으로 수 분 걸린다. 끝에 "총 N개 청크 저장됨" 출력.
- `data/raw/` 캐시는 git에 없으니 노트북마다 처음 1회는 DART에서 받는다(이후 캐시).

---

## 5. 서버 실행 + 동작 확인
```powershell
uv run uvicorn filing_agent.api.main:app --reload --port 8001
```
> 8000이 막혀 있으면(다른 프로세스 점유) `--port 8001` 처럼 바꾼다.

확인 (다른 터미널):
```powershell
# 헬스체크
curl http://127.0.0.1:8001/health

# RAG 질의 (POST)
curl -X POST http://127.0.0.1:8001/ask -H "Content-Type: application/json" -d '{\"question\": \"삼성전자 2024 매출\", \"year\": 2024}'
```
> 💡 **리랭커 첫 호출 시** BGE-reranker-v2-m3 모델(**~600MB**)을 1회 다운로드한다. 첫 질의가 느린 건 정상.
> 이후엔 캐시(`~/.cache/huggingface`)에서 로드한다.

---

## 6. 테스트·린트 (작업 전후 항상)
```powershell
uv run ruff check .
uv run pytest -q
```
키·DB·모델 없이도 통과하도록 설계됨 (네트워크·pgvector·임베딩·리랭킹은 모킹/순수함수 분리).

---

## 7. 트러블슈팅 모음 (실제로 겪은 것들)

| 증상 | 원인 | 해결 |
|---|---|---|
| `uv` 명령 없음 | PATH 미설정 | `C:\Users\<사용자>\.local\bin` PATH 추가 |
| Docker "Virtualization support not detected" | WSL2 미설치 | `wsl --install --no-distribution` → 재시작 |
| DB 연결 인증 실패 / 엉뚱한 PostgreSQL | 5432 포트를 Windows PostgreSQL이 선점 | 프로젝트는 **5433** 사용 (이미 반영됨) |
| `UnicodeDecodeError 0xb8` (DB 연결 시) | psycopg2가 한국어 Windows 에러를 cp949로 받음 | **psycopg(v3)** 사용 (이미 반영됨) |
| 터미널에서 한글/`—`/이모지 출력 시 `UnicodeEncodeError` | PowerShell cp949 인코딩 | 스크립트 print에서 해당 문자 회피 (이미 반영). 필요시 `chcp 65001` |
| 첫 질의가 매우 느림 | 리랭커 모델 최초 다운로드(~600MB) | 1회성. 이후 캐시 |
| `uv sync`가 오래 걸림 | torch 등 대용량(~2GB) | 정상. 네트워크 대기 |

---

## 8. 빠른 재현 요약 (TL;DR)
```powershell
# 1) 도구: Python3.12 / uv / Docker(WSL2) / Git 준비
git clone https://github.com/YoonDaeSung-01/filing-agent.git
cd filing-agent
uv sync
Copy-Item .env.example .env       # → DART_API_KEY, LLM_API_KEY 채우기
docker compose up -d              # pgvector (포트 5433)
uv run python scripts/ingest_all.py
uv run uvicorn filing_agent.api.main:app --reload --port 8001
```

> 이 문서는 환경이 바뀌거나 새 의존성이 추가되면 갱신한다.
> 진행 상황·트러블슈팅 이력은 `docs/phase1_report.md`도 함께 참고.
