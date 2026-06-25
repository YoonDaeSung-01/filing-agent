"""FastAPI 앱 진입점.

- GET  /health : 헬스체크 (키 불필요)
- GET  /ask    : 재무 수치 템플릿 답변 (Phase 0 걷는 해골, DART 키 필요)
- POST /ask    : RAG 기반 공시 질의응답 (Phase 1, LLM 키 + pgvector 필요)

실행: uv run uvicorn filing_agent.api.main:app --reload
"""

from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

from filing_agent.config import get_settings
from filing_agent.ingest import dart_client
from filing_agent.ingest.facts import DartApiError, build_revenue_fact
from filing_agent.llm.client import ask as ask_llm
from filing_agent.retrieval.retriever import search

app = FastAPI(
    title="filing-agent",
    description="DART(한국 전자공시) 기반 공시 사실 추출 API. 투자 조언 도구가 아니다.",
)


# ── GET /health ──────────────────────────────────────────────────────────────

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# ── GET /ask (Phase 0 걷는 해골 — 재무 수치 템플릿) ───────────────────────────

@app.get("/ask")
def ask_revenue(company: str, year: int) -> dict[str, Any]:
    """공시된 매출액을 사실 그대로 추출해 답한다. 데이터 없어도 200 + 안내 메시지."""
    settings = get_settings()
    corp_code = dart_client.resolve_corp_code(settings.dart_api_key, company)
    if corp_code is None:
        return {
            "answer": (
                f"'{company}'의 corp_code 를 찾지 못했습니다. "
                "corpCode.xml 기준 정확한 회사명인지 확인해 주세요."
            ),
            "fact": None,
        }

    prefer = (settings.dart_fs_div, "OFS" if settings.dart_fs_div == "CFS" else "CFS")
    try:
        payload = dart_client.fetch_single_account(
            settings.dart_api_key,
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

    return {
        "answer": (
            f"{company}가 공시한 {year}년 매출액은 약 {fact['value']:,}원입니다. "
            f"(출처: {fact['source']})"
        ),
        "fact": fact,
    }


# ── POST /ask (Phase 1 RAG) ───────────────────────────────────────────────────

class AskRequest(BaseModel):
    question: str
    company: str | None = None  # 선택적 필터
    year: int | None = None     # 선택적 필터


class AskResponse(BaseModel):
    answer: str
    sources: list[str]


@app.post("/ask")
def ask_rag(request: AskRequest) -> AskResponse:
    """공시 서술 텍스트를 RAG 로 검색해 질문에 답한다."""
    settings = get_settings()

    chunks = search(
        request.question,
        settings,
        top_k=5,
        corp_name=request.company,
        year=request.year,
    )

    if not chunks:
        return AskResponse(
            answer=(
                    "공시 자료에서 관련 내용을 찾을 수 없습니다. "
                    "먼저 ingest_all.py 로 데이터를 수집해 주세요."
                ),
            sources=[],
        )

    answer = ask_llm(request.question, list(chunks), settings)
    sources = list(dict.fromkeys(c["source"] for c in chunks))  # 순서 보존 dedup
    return AskResponse(answer=answer, sources=sources)
