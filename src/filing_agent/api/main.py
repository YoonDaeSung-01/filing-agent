"""FastAPI 앱 진입점.

- GET  /health : 헬스체크 (키 불필요)
- GET  /ask    : 재무 수치 템플릿 답변 (Phase 0 걷는 해골, DART 키 필요)
- POST /ask    : LangGraph 에이전트 기반 공시 질의응답 (Phase 3)

실행: uv run uvicorn filing_agent.api.main:app --reload
"""

import logging
from typing import Any

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from filing_agent.config import get_settings
from filing_agent.ingest import dart_client
from filing_agent.ingest.facts import DartApiError, build_revenue_fact
from filing_agent.ingest.stock_client import compute_stock_summary, fetch_stock_ohlc
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


# ── GET /stock ───────────────────────────────────────────────────────────────

@app.get("/stock")
def get_stock(
    company: str,
    period: int = Query(default=365, ge=30, le=1825),
) -> dict[str, Any]:
    """주가 OHLC + 요약 통계. 사실 데이터만. 투자 조언 아님.

    period: 조회 기간(일), 기본 365일(1년). 최소 30일, 최대 1825일(5년).
    """
    settings = get_settings()
    ticker = dart_client.resolve_stock_code(settings.dart_api_key, company)
    if ticker is None:
        reason = (
            f"'{company}'의 종목코드를 찾을 수 없습니다."
            " 비상장이거나 corpCode.xml에 없는 회사입니다."
        )
        return {"found": False, "reason": reason}

    try:
        rows = fetch_stock_ohlc(ticker, period_days=period)
        return compute_stock_summary(rows, company=company, ticker=ticker)
    except Exception as exc:
        logger.exception("주가 조회 실패: company=%r ticker=%r", company, ticker)
        return {"found": False, "reason": str(exc)}


# ── GET /stock/search (상장사 검색) ──────────────────────────────────────────

@app.get("/stock/search")
def search_stocks(q: str, limit: int = 10) -> dict[str, Any]:
    """상장사 이름으로 검색(부분일치). 종목 선택 자동완성용."""
    settings = get_settings()
    results = dart_client.search_listed_companies(settings.dart_api_key, q, limit=limit)
    return {"results": results}


# ── GET /stock/price (한투 실시간 현재가) ────────────────────────────────────

@app.get("/stock/price")
def get_stock_price(company: str) -> dict[str, Any]:
    """한투 KIS 실시간 현재가·당일 시세(사실만). 투자 조언 아님.

    FDR 기반 /stock(과거 차트)과 분리 — 이건 자주 폴링되는 경량 실시간가.
    """
    settings = get_settings()
    ticker = dart_client.resolve_stock_code(settings.dart_api_key, company)
    if ticker is None:
        return {"found": False, "reason": f"'{company}' 종목코드를 찾을 수 없습니다."}
    try:
        from filing_agent.platform.market.kis_market import get_current_price

        data = get_current_price(ticker, settings)
        return {"found": True, "company": company, **data}
    except Exception as exc:
        logger.exception("현재가 조회 실패: company=%r", company)
        return {"found": False, "reason": str(exc)}


# ── 모의투자 (한투 vps) ──────────────────────────────────────────────────────

@app.get("/paper/balance")
def get_paper_balance() -> dict[str, Any]:
    """모의투자 잔고·보유종목·평가손익(사실만). vps."""
    from filing_agent.platform.market.kis_trading import get_balance

    try:
        return {"found": True, **get_balance()}
    except Exception as exc:
        logger.exception("모의투자 잔고 조회 실패")
        return {"found": False, "reason": str(exc)}


class OrderRequest(BaseModel):
    company: str
    side: str  # "buy" | "sell"
    qty: int
    order_type: str = "01"  # 01=시장가, 00=지정가
    price: int = 0


@app.post("/paper/order")
def post_paper_order(req: OrderRequest) -> dict[str, Any]:
    """모의투자 현금 주문(매수/매도)을 위임한다. vps. 실행 주체는 사용자."""
    from filing_agent.platform.market.kis_trading import place_order

    if req.side not in ("buy", "sell"):
        return {"ok": False, "message": f"잘못된 side: {req.side!r}"}
    if req.qty <= 0:
        return {"ok": False, "message": "수량은 1 이상이어야 합니다."}

    settings = get_settings()
    ticker = dart_client.resolve_stock_code(settings.dart_api_key, req.company)
    if ticker is None:
        return {"ok": False, "message": f"'{req.company}' 종목코드를 찾을 수 없습니다."}

    try:
        return place_order(
            ticker,
            req.side,  # type: ignore[arg-type]
            req.qty,
            order_type=req.order_type,
            price=req.price,
            settings=settings,
        )
    except Exception as exc:
        logger.exception("모의투자 주문 실패: %r", req.company)
        return {"ok": False, "message": str(exc)}


# ── GET /financial/trend ─────────────────────────────────────────────────────

@app.get("/financial/trend")
def get_financial_trend(
    company: str,
    account: str,
    years: str = Query(default="2022,2023,2024"),
) -> dict[str, Any]:
    """다년도 재무 추이. 프론트 차트 렌더용. 에이전트 미경유 직통.

    years: 콤마 구분 연도 목록 (예: "2022,2023,2024")
    """
    from filing_agent.agent.tools import _canonical, _get_corp_code, _synonyms_for

    settings = get_settings()

    canonical = _canonical(account)
    if canonical is None:
        return {"found": False, "reason": f"지원하지 않는 계정: {account!r}"}

    try:
        year_list = [int(y.strip()) for y in years.split(",")]
    except ValueError:
        return {"found": False, "reason": f"잘못된 years 형식: {years!r}"}

    corp_code = _get_corp_code(company, settings.dart_api_key)
    if corp_code is None:
        return {"found": False, "reason": f"회사를 찾을 수 없음: {company!r}"}

    points: list[dict] = []
    for year in year_list:
        try:
            payload = dart_client.fetch_single_account(
                settings.dart_api_key,
                corp_code=corp_code,
                bsns_year=year,
                reprt_code=settings.dart_report_code,
            )
        except Exception:
            continue

        found = False
        for synonym in _synonyms_for(canonical):
            fact = build_revenue_fact(payload, company=company, account_nm=synonym, year=year)
            if fact is not None:
                points.append({"year": year, "value": fact["value"], "fs_div": fact["fs_div"]})
                found = True
                break
        if not found:
            points.append({"year": year, "value": None, "fs_div": None})

    return {
        "found": True,
        "company": company,
        "account": canonical,
        "points": points,
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
