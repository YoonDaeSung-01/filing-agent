"""에이전트 도구 3종 — doc_search / financial_lookup / compute_change.

모든 도구는 langchain @tool 데코레이터로 정의한다.
숫자 관련 도구는 **타입 있는 구조화 값**을 반환해 LLM이 숫자를 텍스트에서 베끼지 않게 한다.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from langchain_core.tools import tool

from filing_agent.ingest.dart_client import fetch_single_account, resolve_corp_code
from filing_agent.ingest.facts import build_revenue_fact, extract_change

# ---------------------------------------------------------------------------
# 표준계정 정규화 — 회사·업종마다 다른 계정명을 표준 5개로 흡수
# ---------------------------------------------------------------------------
ACCOUNT_SYNONYMS: dict[str, set[str]] = {
    "매출액": {"매출액", "수익(매출액)", "영업수익", "매출", "수익"},
    "영업이익": {"영업이익", "영업이익(손실)"},
    "당기순이익": {"당기순이익", "당기순이익(손실)", "분기순이익", "반기순이익"},
    "자산총계": {"자산총계"},
    "부채총계": {"부채총계"},
}

CANONICAL_ACCOUNTS = list(ACCOUNT_SYNONYMS.keys())


def _canonical(account: str) -> str | None:
    """사용자 입력 → 표준 계정명. 못 찾으면 None."""
    for canonical, synonyms in ACCOUNT_SYNONYMS.items():
        if account in synonyms or account == canonical:
            return canonical
    return None


def _synonyms_for(canonical: str) -> set[str]:
    return ACCOUNT_SYNONYMS.get(canonical, {canonical})


# ---------------------------------------------------------------------------
# corp_code 캐시 (회사명 → corp_code, 1회 로드)
# ---------------------------------------------------------------------------
_CORP_CODE_CACHE_PATH = Path("data/raw/corp_code_map.json")


def _load_cached_corp_map() -> dict[str, str]:
    if _CORP_CODE_CACHE_PATH.exists():
        return json.loads(_CORP_CODE_CACHE_PATH.read_text(encoding="utf-8"))
    return {}


def _get_corp_code(company: str, api_key: str) -> str | None:
    corp_map = _load_cached_corp_map()
    if company in corp_map:
        return corp_map[company]
    return resolve_corp_code(api_key, company)


# ---------------------------------------------------------------------------
# 도구 공통 설정 접근 헬퍼
# ---------------------------------------------------------------------------
def _settings() -> Any:
    from filing_agent.config import get_settings
    return get_settings()


# ---------------------------------------------------------------------------
# 도구 1: doc_search — 공시 서술 의미 검색
# ---------------------------------------------------------------------------
@tool
def doc_search(
    query: str,
    company: str | None = None,
    year: int | None = None,
) -> list[dict]:
    """공시 '서술' 내용(사업 위험·전략·경영진단·사업 현황 등)을 의미 검색한다.

    수치(매출/이익 등 재무 숫자)는 financial_lookup 을 쓸 것.
    반환: [{content: str, source: str, score: float}, ...]
    """
    from filing_agent.retrieval.retriever import search
    cfg = _settings()
    chunks = search(query, cfg, corp_name=company, year=year)
    return [
        {"content": c["content"], "source": c.get("source", ""), "score": c.get("score", 0.0)}
        for c in chunks
    ]


# ---------------------------------------------------------------------------
# 도구 2: financial_lookup — 재무 수치 구조화 조회
# ---------------------------------------------------------------------------
@tool
def financial_lookup(
    company: str,
    account: str,
    year: int,
) -> dict:
    """공시된 재무 '수치'를 타입 있는 값으로 반환한다.
    account 는 {매출액, 영업이익, 당기순이익, 자산총계, 부채총계} 중 하나.
    반환: {company, account, year, value(원), fs_div, source} | {found: False, reason}
    """
    cfg = _settings()
    canonical = _canonical(account)
    if canonical is None:
        return {
            "found": False,
            "reason": f"지원하지 않는 계정: {account!r}. 허용: {CANONICAL_ACCOUNTS}",
        }

    corp_code = _get_corp_code(company, cfg.dart_api_key)
    if corp_code is None:
        return {"found": False, "reason": f"회사를 찾을 수 없음: {company!r}"}

    try:
        payload = fetch_single_account(
            cfg.dart_api_key,
            corp_code=corp_code,
            bsns_year=year,
            reprt_code=cfg.dart_report_code,
        )
    except Exception as exc:
        return {"found": False, "reason": str(exc)}

    # 동의어 집합 순회로 계정 매칭
    for synonym in _synonyms_for(canonical):
        fact = build_revenue_fact(payload, company=company, account_nm=synonym, year=year)
        if fact is not None:
            return dict(fact)

    return {
        "found": False,
        "reason": f"{company} {year}년 {canonical} 데이터 없음(CFS·OFS 모두 미수록)",
    }


# ---------------------------------------------------------------------------
# 도구 3: compute_change — 증감 계산 (도구 내부에서 처리)
# ---------------------------------------------------------------------------
@tool
def compute_change(
    company: str,
    account: str,
    year_from: int,
    year_to: int,
) -> dict:
    """두 연도 사이 증감액·증감률을 도구 내부에서 계산해 반환한다.
    LLM 은 회사명·계정·연도 식별자만 전달하고 숫자를 직접 계산하지 않는다.
    반환: {company, account, year_from, value_from, year_to, value_to,
           delta(원), pct_change(%), fs_div, source} | {found: False, reason}
    """
    cfg = _settings()
    canonical = _canonical(account)
    if canonical is None:
        return {
            "found": False,
            "reason": f"지원하지 않는 계정: {account!r}. 허용: {CANONICAL_ACCOUNTS}",
        }

    corp_code = _get_corp_code(company, cfg.dart_api_key)
    if corp_code is None:
        return {"found": False, "reason": f"회사를 찾을 수 없음: {company!r}"}

    # year_to 보고서 1개로 당기/전기를 동시에 커버하는 최적 경로
    if year_from == year_to - 1:
        try:
            payload = fetch_single_account(
                cfg.dart_api_key,
                corp_code=corp_code,
                bsns_year=year_to,
                reprt_code=cfg.dart_report_code,
            )
        except Exception as exc:
            return {"found": False, "reason": str(exc)}

        for synonym in _synonyms_for(canonical):
            pair = extract_change(payload, company=company, account_nm=synonym, year_to=year_to)
            if pair is not None:
                fact_from, fact_to = pair
                delta = fact_to["value"] - fact_from["value"]
                denom = abs(fact_from["value"])
                pct = round(delta / denom * 100, 1) if denom != 0 else None
                return {
                    "company": company,
                    "account": canonical,
                    "year_from": year_from,
                    "value_from": fact_from["value"],
                    "year_to": year_to,
                    "value_to": fact_to["value"],
                    "delta": delta,
                    "pct_change": pct,
                    "fs_div": fact_from["fs_div"],
                    "source": fact_from["source"],
                }
        return {
            "found": False,
            "reason": f"{company} {year_to}년 {canonical} 전기/당기 데이터 없음",
        }

    # 두 파일 각각 로드
    results = []
    for yr in (year_from, year_to):
        try:
            payload = fetch_single_account(
                cfg.dart_api_key,
                corp_code=corp_code,
                bsns_year=yr,
                reprt_code=cfg.dart_report_code,
            )
        except Exception as exc:
            return {"found": False, "reason": f"{yr}년 조회 실패: {exc}"}

        fact = None
        for synonym in _synonyms_for(canonical):
            fact = build_revenue_fact(payload, company=company, account_nm=synonym, year=yr)
            if fact is not None:
                break
        if fact is None:
            return {"found": False, "reason": f"{company} {yr}년 {canonical} 데이터 없음"}
        results.append(fact)

    f, t = results
    delta = t["value"] - f["value"]
    denom = abs(f["value"])
    pct = round(delta / denom * 100, 1) if denom != 0 else None
    return {
        "company": company,
        "account": canonical,
        "year_from": year_from,
        "value_from": f["value"],
        "year_to": year_to,
        "value_to": t["value"],
        "delta": delta,
        "pct_change": pct,
        "fs_div": f["fs_div"],
        "source": f["source"],
    }


TOOLS = [doc_search, financial_lookup, compute_change]
