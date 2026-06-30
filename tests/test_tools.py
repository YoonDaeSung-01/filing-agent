"""agent/tools.py 단위 테스트 — 키·네트워크·DB 불필요.

도구 내부의 순수 로직(표준계정 정규화, compute_change 계산)을 픽스처로 검증한다.
실제 DART API 호출은 dart_client 를 모킹해 분리한다.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from filing_agent.agent.tools import (
    ACCOUNT_SYNONYMS,
    CANONICAL_ACCOUNTS,
    _canonical,
    compute_change,
    compute_sum,
    doc_search,
    financial_lookup,
)

# ── 픽스처 로드 ──────────────────────────────────────────────────────────────
FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _load(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


CFS_PAYLOAD = _load("fnlttSinglAcnt_cfs_ok.json")
OFS_PAYLOAD = _load("fnlttSinglAcnt_ofs_fallback.json")
NO_DATA_PAYLOAD = _load("fnlttSinglAcnt_no_data_013.json")


# ── 표준계정 정규화 ──────────────────────────────────────────────────────────
class TestCanonical:
    def test_exact_match(self) -> None:
        assert _canonical("매출액") == "매출액"

    def test_synonym_match(self) -> None:
        assert _canonical("영업수익") == "매출액"
        assert _canonical("영업이익(손실)") == "영업이익"

    # ── 신규 계정 정규화 ──────────────────────────────────────────────────
    def test_자본총계_exact(self) -> None:
        assert _canonical("자본총계") == "자본총계"

    def test_자본총계_synonym_자기자본(self) -> None:
        assert _canonical("자기자본") == "자본총계"

    def test_자본총계_synonym_총자본(self) -> None:
        assert _canonical("총자본") == "자본총계"

    def test_법인세차감전순이익_no_space(self) -> None:
        assert _canonical("법인세차감전순이익") == "법인세차감전순이익"

    def test_법인세차감전순이익_dart_format_with_space(self) -> None:
        # DART가 실제로 반환하는 형식 (공백 포함) — 동의어 집합에 포함돼야 함
        assert _canonical("법인세차감전 순이익") == "법인세차감전순이익"

    def test_법인세차감전순이익_synonym_세전이익(self) -> None:
        assert _canonical("세전이익") == "법인세차감전순이익"

    def test_총포괄손익_exact(self) -> None:
        assert _canonical("총포괄손익") == "총포괄손익"

    def test_총포괄손익_synonym_포괄이익(self) -> None:
        assert _canonical("포괄이익") == "총포괄손익"

    def test_영업활동현금흐름_not_supported(self) -> None:
        # CF 계정은 fnlttSinglAcnt 미지원 → None 반환
        assert _canonical("영업활동현금흐름") is None
        assert _canonical("투자활동현금흐름") is None

    def test_unknown_returns_none(self) -> None:
        assert _canonical("존재하지않는계정") is None

    def test_all_canonicals_in_synonyms(self) -> None:
        for c in CANONICAL_ACCOUNTS:
            assert c in ACCOUNT_SYNONYMS


# ── financial_lookup (모킹) ──────────────────────────────────────────────────
class TestFinancialLookup:
    def _invoke(self, company: str, account: str, year: int, payload: dict) -> dict:
        with (
            patch("filing_agent.agent.tools._get_corp_code", return_value="00126380"),
            patch("filing_agent.agent.tools.fetch_single_account", return_value=payload),
        ):
            return financial_lookup.invoke({"company": company, "account": account, "year": year})

    def test_cfs_lookup_returns_value(self) -> None:
        result = self._invoke("삼성전자", "매출액", 2024, CFS_PAYLOAD)
        assert result.get("found") is not False
        assert result["value"] == 300_870_903_000_000
        assert result["fs_div"] == "CFS"
        assert result["company"] == "삼성전자"

    def test_synonym_account(self) -> None:
        result = self._invoke("삼성전자", "영업수익", 2024, CFS_PAYLOAD)
        assert result.get("found") is not False
        assert result["value"] == 300_870_903_000_000

    def test_unknown_account_returns_not_found(self) -> None:
        result = self._invoke("삼성전자", "없는계정", 2024, CFS_PAYLOAD)
        assert result["found"] is False

    def test_unknown_company_returns_not_found(self) -> None:
        with patch("filing_agent.agent.tools._get_corp_code", return_value=None):
            result = financial_lookup.invoke(
                {"company": "없는회사", "account": "매출액", "year": 2024}
            )
        assert result["found"] is False

    def test_ofs_fallback(self) -> None:
        result = self._invoke("테스트회사", "매출액", 2024, OFS_PAYLOAD)
        assert result.get("found") is not False
        assert result["fs_div"] == "OFS"

    # ── 신규 계정 조회 ────────────────────────────────────────────────────
    def test_자본총계_lookup(self) -> None:
        result = self._invoke("삼성전자", "자본총계", 2024, CFS_PAYLOAD)
        assert result.get("found") is not False
        assert result["value"] == 402_192_070_000_000
        assert result["fs_div"] == "CFS"

    def test_자기자본_synonym_lookup(self) -> None:
        result = self._invoke("삼성전자", "자기자본", 2024, CFS_PAYLOAD)
        assert result.get("found") is not False
        assert result["value"] == 402_192_070_000_000

    def test_법인세차감전순이익_lookup(self) -> None:
        result = self._invoke("삼성전자", "법인세차감전순이익", 2024, CFS_PAYLOAD)
        assert result.get("found") is not False
        assert result["value"] == 37_529_734_000_000

    def test_세전이익_synonym_lookup(self) -> None:
        result = self._invoke("삼성전자", "세전이익", 2024, CFS_PAYLOAD)
        assert result.get("found") is not False
        assert result["value"] == 37_529_734_000_000

    def test_총포괄손익_lookup(self) -> None:
        result = self._invoke("삼성전자", "총포괄손익", 2024, CFS_PAYLOAD)
        assert result.get("found") is not False
        assert result["value"] == 51_296_338_000_000

    def test_영업활동현금흐름_not_supported(self) -> None:
        result = self._invoke("삼성전자", "영업활동현금흐름", 2024, CFS_PAYLOAD)
        assert result["found"] is False
        assert "지원하지 않는 계정" in result["reason"]


# ── compute_change (모킹) ────────────────────────────────────────────────────
class TestComputeChange:
    def _invoke(
        self, company: str, account: str, year_from: int, year_to: int, payload: dict
    ) -> dict:
        with (
            patch("filing_agent.agent.tools._get_corp_code", return_value="00126380"),
            patch("filing_agent.agent.tools.fetch_single_account", return_value=payload),
        ):
            return compute_change.invoke({
                "company": company,
                "account": account,
                "year_from": year_from,
                "year_to": year_to,
            })

    def test_change_values(self) -> None:
        result = self._invoke("삼성전자", "매출액", 2023, 2024, CFS_PAYLOAD)
        assert result.get("found") is not False
        assert result["value_to"] == 300_870_903_000_000
        assert result["value_from"] == 258_935_494_000_000
        assert result["delta"] == 300_870_903_000_000 - 258_935_494_000_000

    def test_pct_change_calculation(self) -> None:
        result = self._invoke("삼성전자", "매출액", 2023, 2024, CFS_PAYLOAD)
        expected_pct = round(
            (300_870_903_000_000 - 258_935_494_000_000) / 258_935_494_000_000 * 100, 1
        )
        assert result["pct_change"] == pytest.approx(expected_pct, abs=0.1)

    def test_unknown_account(self) -> None:
        result = self._invoke("삼성전자", "없는계정", 2023, 2024, CFS_PAYLOAD)
        assert result["found"] is False


# ── compute_sum (모킹) ───────────────────────────────────────────────────────
class TestComputeSum:
    def _invoke(self, companies: list[str], account: str, year: int, payload: dict) -> dict:
        with (
            patch("filing_agent.agent.tools._get_corp_code", return_value="00126380"),
            patch("filing_agent.agent.tools.fetch_single_account", return_value=payload),
        ):
            return compute_sum.invoke(
                {"companies": companies, "account": account, "year": year}
            )

    def test_two_company_sum(self) -> None:
        result = self._invoke(["삼성전자", "SK하이닉스"], "매출액", 2024, CFS_PAYLOAD)
        assert result.get("found") is not False
        # 모킹이 두 회사에 같은 페이로드를 주므로 total = 2 × 매출액
        assert result["total"] == 2 * 300_870_903_000_000
        assert len(result["values"]) == 2
        assert isinstance(result["source"], list) and len(result["source"]) == 2

    def test_single_company_rejected(self) -> None:
        result = self._invoke(["삼성전자"], "매출액", 2024, CFS_PAYLOAD)
        assert result["found"] is False
        assert "2곳 이상" in result["reason"]

    def test_unknown_account(self) -> None:
        result = self._invoke(["삼성전자", "SK하이닉스"], "없는계정", 2024, CFS_PAYLOAD)
        assert result["found"] is False

    def test_missing_company_data_fails(self) -> None:
        with (
            patch("filing_agent.agent.tools._get_corp_code", return_value=None),
            patch("filing_agent.agent.tools.fetch_single_account", return_value=CFS_PAYLOAD),
        ):
            result = compute_sum.invoke(
                {"companies": ["없는회사", "삼성전자"], "account": "매출액", "year": 2024}
            )
        assert result["found"] is False


# ── doc_search (retriever.search 위임 검증) ──────────────────────────────────
class TestDocSearch:
    def test_delegates_to_search_and_maps_fields(self) -> None:
        fake_chunks = [
            {"content": "주요 위험은 환율", "source": "삼성전자 사업보고서 2024",
             "corp_name": "삼성전자", "year": 2024, "score": 0.9},
        ]
        # retriever.search 를 모킹(실제 DB·임베딩 불필요)
        with patch("filing_agent.retrieval.retriever.search", return_value=fake_chunks):
            result = doc_search.invoke(
                {"query": "사업 위험", "company": "삼성전자", "year": 2024}
            )
        assert result == [
            {"content": "주요 위험은 환율", "source": "삼성전자 사업보고서 2024", "score": 0.9}
        ]
