"""FastAPI 앱 진입점.

- GET /health: 헬스체크(키 불필요).
- GET /ask: DART 에서 매출액을 조회해 결정론적 템플릿 문자열로 답한다(키 필요).
  이 단계에는 LLM/에이전트가 없다 — '답변'은 구조화 값 + 템플릿이면 충분하다.

실행: ``uv run uvicorn filing_agent.api.main:app --reload``
"""

from typing import Any

from fastapi import FastAPI

from filing_agent.config import get_settings
from filing_agent.ingest import dart_client
from filing_agent.ingest.facts import DartApiError, build_revenue_fact

app = FastAPI(
    title="filing-agent",
    description="DART(한국 전자공시) 기반 공시 사실 추출 API. 투자 조언 도구가 아니다.",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ask")
def ask(company: str, year: int) -> dict[str, Any]:
    """공시된 매출액을 사실 그대로 추출해 답한다.

    데이터를 못 찾아도 500 이 아니라 200 + 명확한 안내 메시지를 반환한다.
    """
    settings = get_settings()
    api_key = settings.dart_api_key

    corp_code = dart_client.resolve_corp_code(api_key, company)
    if corp_code is None:
        return {
            "answer": (
                f"'{company}'의 corp_code 를 찾지 못했습니다. "
                "corpCode.xml 기준 정확한 회사명인지 확인해 주세요."
            ),
            "fact": None,
        }

    other = "OFS" if settings.dart_fs_div == "CFS" else "CFS"
    prefer = (settings.dart_fs_div, other)
    try:
        payload = dart_client.fetch_single_account(
            api_key,
            corp_code=corp_code,
            bsns_year=year,
            reprt_code=settings.dart_report_code,
        )
        fact = build_revenue_fact(payload, company=company, year=year, prefer=prefer)
    except DartApiError as exc:
        return {
            "answer": (
                f"{company} {year}년 매출액을 공시 데이터에서 찾지 못했습니다 "
                f"(DART status={exc.status})."
            ),
            "fact": None,
        }

    if fact is None:
        return {
            "answer": f"{company} {year}년 매출액을 공시 데이터에서 찾지 못했습니다.",
            "fact": None,
        }

    answer = (
        f"{company}가 공시한 {year}년 매출액은 약 {fact['value']:,}원입니다. "
        f"(출처: {fact['source']})"
    )
    return {"answer": answer, "fact": fact}
