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
