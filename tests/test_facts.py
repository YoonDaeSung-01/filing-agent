"""facts.py 검증 — 픽스처만 사용(네트워크/키 불필요)."""

import json
from pathlib import Path

import pytest

from filing_agent.ingest.facts import (
    DartApiError,
    build_revenue_fact,
    extract_account,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_extract_account_parses_cfs_revenue_as_int() -> None:
    # (a) 콤마 포함 문자열을 콤마 없는 int 로, 올바른 구조로 추출
    payload = _load("fnlttSinglAcnt_cfs_ok.json")
    fact = extract_account(payload, company="삼성전자", fs_div="CFS", year=2024)

    assert fact is not None
    assert fact["value"] == 300_870_903_000_000
    assert isinstance(fact["value"], int)
    assert fact["account"] == "매출액"
    assert fact["fs_div"] == "CFS"
    assert fact["company"] == "삼성전자"
    assert fact["year"] == 2024
    assert "fnlttSinglAcnt" in fact["source"]


def test_build_revenue_fact_falls_back_to_ofs() -> None:
    # (b) CFS 에 매출액이 없으면 OFS 로 폴백
    payload = _load("fnlttSinglAcnt_ofs_fallback.json")

    assert extract_account(payload, company="테스트기업", fs_div="CFS") is None

    fact = build_revenue_fact(payload, company="테스트기업", year=2023)
    assert fact is not None
    assert fact["fs_div"] == "OFS"
    assert fact["value"] == 105_000_000_000
    assert isinstance(fact["value"], int)


def test_non_ok_status_raises() -> None:
    # (c) status 가 "000" 이 아니면 명확한 예외
    payload = _load("fnlttSinglAcnt_no_data_013.json")

    with pytest.raises(DartApiError) as exc:
        extract_account(payload, company="삼성전자")
    assert exc.value.status == "013"

    with pytest.raises(DartApiError):
        build_revenue_fact(payload, company="삼성전자")
