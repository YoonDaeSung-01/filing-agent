# filing-agent

DART(한국 전자공시) 자료를 근거로 재무 수치를 **출처와 함께** 답하는 재무 질의응답 어시스턴트.

> 이 단계는 "걷는 해골(walking skeleton)"입니다. LLM·에이전트·벡터DB·RAG 없이,
> DART에서 단일 기업·단일 계정(삼성전자 매출액)을 조회해 결정론적 템플릿으로 답합니다.

## 빠른 시작

요구사항: [uv](https://docs.astral.sh/uv/) (Python 3.12 는 uv가 자동 설치).

```bash
# 1) 의존성 동기화 (가상환경 + 패키지 설치)
uv sync

# 2) 인증키 설정: .env.example 을 복사해 .env 를 만들고 키를 채운다.
#    OpenDART 키는 https://opendart.fss.or.kr 에서 무료 발급.
cp .env.example .env          # Windows PowerShell: Copy-Item .env.example .env
#    그런 다음 .env 의 DART_API_KEY= 에 발급받은 키를 넣는다.

# 3) 서버 실행
uv run uvicorn filing_agent.api.main:app --reload
```

### 엔드포인트
- `GET /health` → `{"status": "ok"}` — 키 불필요.
- `GET /ask?company=삼성전자&year=2024` → 매출액 + 출처 — 키 필요(Phase B).

### 개발 점검
```bash
uv run ruff check     # 린트
uv run pytest         # 테스트 (키 없이 통과)
```

## 한계
- **이 도구는 투자 조언이 아니라 공시 사실 추출 도구입니다.** "이 주식 사야 하나?" 같은
  매수/매도 추천에는 답하지 않습니다. 공시에 기재된 사실(재무 수치 등)을 출처와 함께
  추출·전달하는 것만을 목표로 합니다.
- 현재 범위는 단일 기업·단일 계정(삼성전자 매출액)뿐입니다.

## 데이터 출처
- **OpenDART** — 금융감독원 전자공시시스템 오픈 API, https://opendart.fss.or.kr
  - 회사 고유번호(corp_code) 매핑: `corpCode.xml`
  - 재무 주요계정: `fnlttSinglAcnt.json`
