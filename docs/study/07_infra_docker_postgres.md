# 07. 인프라 — Docker · PostgreSQL · psycopg (★★★)

> "컨테이너 써봤어요"를 원리와 실제 트러블슈팅으로 뒷받침.

---

## 7-1. Docker · Docker Compose

### 한 줄 정의
> **Docker** = 앱+의존성을 격리된 컨테이너로 패키징·실행. **Compose** = 여러 컨테이너를 YAML로 선언적으로 함께 실행.

### 작동 원리 (VM과 차이)
- **컨테이너 vs VM**:
  - VM = 게스트 OS 전체를 가상화(무겁다).
  - 컨테이너 = **호스트 커널을 공유**하고 프로세스만 격리(가볍다, 빠르다).
- **이미지(image)** = 실행에 필요한 파일 스냅샷(읽기 전용). **컨테이너** = 이미지의 실행 인스턴스.
- **포트 매핑** `호스트:컨테이너` — 컨테이너 내부 포트를 호스트로 노출.
- **볼륨(volume)** — 컨테이너가 죽어도 데이터 유지(영속화).

### 이 프로젝트에서 실제 사용 (docker-compose.yml)
- `pgvector/pgvector:pg17` 이미지로 Postgres+pgvector를 한 번에.
- `ports: "5433:5432"` — **호스트 5433** → 컨테이너 5432.
- `volumes: pgdata` — DB 데이터 영속화.
- `healthcheck` — `pg_isready`로 준비 상태 확인.
- 실행: `docker compose up -d`(백그라운드), `docker ps`(상태), `docker compose down`(정리).

### ⚠️ 실제 겪은 함정 (면접 스토리감)
- **증상**: 컨테이너는 healthy인데 파이썬 연결이 인증 실패.
- **원인**: 호스트에 **Windows용 PostgreSQL 16 서비스가 5432를 선점** → 파이썬이 Docker가 아니라 그 네이티브 PG로 붙고 있었음.
- **진단**: `netstat -ano | findstr :5432` → 두 프로세스가 동시 LISTEN.
- **해결**: 컨테이너를 **5433:5432**로 매핑(+config 기본 DSN도 5433). 어느 노트북이든 5433 사용으로 통일.

### 면접 Q&A
**Q. 컨테이너와 VM 차이는?**
> VM은 게스트 OS 전체를 가상화해 무겁고, 컨테이너는 호스트 커널을 공유하고 프로세스만 격리해 가볍고 빠릅니다. 그래서 의존 서비스(pgvector)를 빠르게 띄우고 정리하기 좋았습니다.

**Q. docker compose를 왜 쓰나요?**
> DB 같은 의존 서비스를 코드(YAML)로 선언해 `docker compose up` 한 줄로 재현 가능하게 띄우려고요. 포트·볼륨·헬스체크를 명시해 환경 차이를 줄였습니다.

**Q. (트러블슈팅) 연결이 안 됐던 경험은?**
> 호스트의 기존 PostgreSQL이 5432를 선점해 컨테이너 대신 그쪽으로 붙는 문제가 있었습니다. netstat으로 포트 점유를 확인하고 컨테이너를 5433으로 매핑해 해결했습니다.

### 🎴 암기 카드
- 컨테이너 = 커널 공유, 프로세스 격리(VM보다 가벼움)
- 이미지(스냅샷) → 컨테이너(인스턴스)
- 포트 호스트:컨테이너, 볼륨=영속화
- 함정: 5432 선점 → 5433 매핑 (netstat 진단)

---

## 7-2. WSL2

### 한 줄 정의
> Windows에서 진짜 Linux 커널을 돌리는 계층. Docker Desktop의 백엔드.

### 왜 / 겪은 함정
- Docker Desktop이 Linux 컨테이너를 돌리려면 WSL2(또는 Hyper-V) 필요.
- **증상**: "Virtualization support not detected" → **원인**: BIOS 가상화는 ON이었지만 **WSL2 미설치**.
- **해결**: 관리자 PowerShell `wsl --install --no-distribution` → 재시작.

### 면접 Q&A
**Q. Windows에서 컨테이너 개발 환경은 어떻게 구성했나요?**
> Docker Desktop을 WSL2 백엔드로 구동했습니다. WSL2 미설치로 가상화 인식이 안 되는 이슈가 있어 wsl --install 후 재시작으로 해결했습니다.

### 🎴 암기 카드
- WSL2 = Windows 위 Linux 커널, Docker 백엔드
- "Virtualization not detected" = WSL2 미설치 가능성
- wsl --install --no-distribution → 재시작

---

## 7-3. PostgreSQL · psycopg (v3)

### PostgreSQL
- 오픈소스 관계형 DB. **확장 생태계**가 강함(pgvector도 확장).
- 이 프로젝트: 관계형(메타데이터) + 벡터(pgvector)를 한 DB에서.

### psycopg — Python ↔ Postgres 드라이버
- **v2(psycopg2)**: 오래된 표준.
- **v3(psycopg)**: 현대적 재작성. 이 프로젝트가 v3로 갈아탐.

### ⚠️ 왜 v3로 갈아탔나 (면접 스토리감)
- **증상**: DB 연결 시 `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xb8`.
- **원인**: psycopg2가 libpq의 **연결 실패 에러 메시지(한국어, cp949)** 를 UTF-8로 디코딩하려다 크래시 → **진짜 에러(인증 실패)가 가려짐**.
- **해결**: psycopg(v3)로 교체 → 인코딩을 올바르게 처리 → 진짜 원인(5432 포트 충돌)을 볼 수 있었음.
- 코드: DSN을 `urlparse`로 분해해 host/port/dbname/user/password로 명시 연결, `register_vector`로 pgvector 타입 등록.

### 면접 Q&A
**Q. 드라이버 때문에 디버깅이 어려웠던 경험은?**
> psycopg2가 Windows 한국어 환경에서 libpq 에러 메시지를 cp949로 받는데 UTF-8로 디코딩하다 크래시했습니다. 그 바람에 진짜 원인인 인증 실패가 가려졌죠. psycopg v3로 바꾸니 에러가 제대로 보였고, 그제서야 포트 선점 문제를 찾았습니다. "에러를 가리는 에러"를 걷어낸 경험입니다.

### 🎴 암기 카드
- Postgres = 관계형 + 확장(pgvector)
- psycopg2 → v3 전환: 한국어 cp949 에러 디코딩 크래시 회피
- v3가 진짜 에러를 보여줘 5432 충돌 발견
- urlparse로 DSN 분해 + register_vector

---

## 7-4. 환경 트러블슈팅 종합 (이 프로젝트 실전)

| 증상 | 원인 | 해결 |
|---|---|---|
| Docker "Virtualization not detected" | WSL2 미설치 | wsl --install → 재시작 |
| DB 인증 실패(엉뚱한 PG) | 호스트 PG가 5432 선점 | 컨테이너 5433 매핑 |
| `UnicodeDecodeError 0xb8` | psycopg2 cp949 에러 디코딩 | psycopg v3 전환 |
| 터미널 한글/이모지 `UnicodeEncodeError` | PowerShell cp949 | print 문자 회피 / `chcp 65001` |
| 첫 질의 매우 느림 | 리랭커 모델 최초 다운로드(~600MB) | 1회성, 이후 캐시 |

> 이 표는 그대로 면접의 "트러블슈팅 경험" 답변 소재가 된다. 각 항목 = "증상→진단→원인→해결" 4단.
