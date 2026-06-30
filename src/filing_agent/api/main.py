"""FastAPI 앱 진입점.

- GET  /health : 헬스체크 (키 불필요)
- GET  /ask    : 재무 수치 템플릿 답변 (Phase 0 걷는 해골, DART 키 필요)
- POST /ask    : LangGraph 에이전트 기반 공시 질의응답 (Phase 3)

실행: uv run uvicorn filing_agent.api.main:app --reload
"""

import logging
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from filing_agent.config import get_settings
from filing_agent.ingest import dart_client
from filing_agent.ingest.facts import DartApiError, build_revenue_fact
from filing_agent.logging_config import configure_logging
from filing_agent.observability import configure_observability, get_langfuse_callbacks

configure_logging()
configure_observability()  # 키 있을 때만 Langfuse 트레이싱(없으면 no-op)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="filing-agent",
    description="DART(한국 전자공시) 기반 공시 사실 추출 API. 투자 조언 도구가 아니다.",
)

# 프론트엔드(Next.js dev 서버)에서의 교차 출처 호출 허용.
# 운영 배포 시 allow_origins 를 실제 도메인으로 좁힐 것.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
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


# ── POST /ask (Phase 3 에이전트) ─────────────────────────────────────────────

class AskRequest(BaseModel):
    question: str
    company: str | None = None
    year: int | None = None


class AskResponse(BaseModel):
    answer: str
    sources: list[str]
    tool_log: list[dict] = []  # 도구 호출 과정 노출(디버그·데모용)
    facts: list[dict] = []     # 수치 도구의 구조화 결과(프론트 카드 렌더용·성공 결과만)
    status: str = "ok"         # "ok" | "blocked"(가드레일) | "failed"(우아한 실패) — 프론트 분기용


@app.post("/ask")
def ask_agent(request: AskRequest) -> AskResponse:
    """LangGraph 에이전트가 도구를 골라 공시 질문에 답한다."""
    from filing_agent.agent.graph import get_graph
    from filing_agent.agent.state import AgentState

    graph = get_graph()
    initial: AgentState = {
        "question": request.question,
        "company": request.company,
        "year": request.year,
        "messages": [],
        "tool_log": [],
        "steps": 0,
        "facts": [],
        "doc_sources": [],
        "draft": None,
        "figures": [],
        "verifier_feedback": None,
        "verify_attempts": 0,
        "status": None,
        "answer": None,
        "sources": [],
    }
    try:
        # 키 있으면 Langfuse 핸들러로 전체 그래프를 트레이싱(없으면 빈 리스트)
        final = graph.invoke(initial, config={"callbacks": get_langfuse_callbacks()})
    except Exception:
        logger.exception("에이전트 실행 실패: question=%r", request.question)
        return AskResponse(
            answer="요청 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
            sources=[],
            tool_log=[],
            status="failed",
        )
    return AskResponse(
        answer=final.get("answer") or "",
        sources=final.get("sources") or [],
        tool_log=final.get("tool_log") or [],
        facts=final.get("facts") or [],
        status=final.get("status") or "ok",
    )
