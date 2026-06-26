"""회귀 게이트 — 키·모델·DB 없이 도는 결정론 검증.

1. 채점 함수(metrics.py)가 알려진 예측/정답에 기대 점수를 낸다.
2. 픽스처로 모킹된 DART 페이로드에서 financial_lookup/compute_change가
   expected_value와 일치하는 값을 반환한다.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from filing_agent.agent.tools import compute_change, financial_lookup
from filing_agent.eval.metrics import number_accuracy, routing_accuracy
from filing_agent.eval.schema import load_jsonl

FIXTURE_DIR = Path(__file__).parent / "fixtures"
SAMPLE_JSONL = FIXTURE_DIR / "goldset_sample.jsonl"
CFS_PAYLOAD = json.loads(
    (FIXTURE_DIR / "fnlttSinglAcnt_cfs_ok.json").read_text(encoding="utf-8")
)
OFS_PAYLOAD = json.loads(
    (FIXTURE_DIR / "fnlttSinglAcnt_ofs_fallback.json").read_text(encoding="utf-8")
)


# ── 채점 로직 정합성 ──────────────────────────────────────────────────────────
class TestMetricsScoringLogic:
    """metrics.py 순수 함수가 알려진 입력에 기대 점수를 내는지 검증."""

    GOLD = [
        {"id": "g1", "type": "lookup", "expected_value": 100,
         "expected_tools": ["financial_lookup"]},
        {"id": "g2", "type": "calc", "expected_value": 50, "expected_tools": ["compute_change"]},
        {"id": "g3", "type": "routing", "expected_value": None, "expected_tools": ["doc_search"]},
    ]

    def test_number_accuracy_perfect(self) -> None:
        preds = [
            {"id": "g1", "predicted_value": 100},
            {"id": "g2", "predicted_value": 50},
        ]
        assert number_accuracy(preds, self.GOLD) == 1.0

    def test_number_accuracy_zero(self) -> None:
        preds = [{"id": "g1", "predicted_value": 999}]
        assert number_accuracy(preds, self.GOLD) == 0.0

    def test_routing_accuracy_perfect(self) -> None:
        preds = [
            {"id": "g1", "predicted_tools": ["financial_lookup"]},
            {"id": "g3", "predicted_tools": ["doc_search"]},
        ]
        assert routing_accuracy(preds, self.GOLD) == 1.0

    def test_routing_accuracy_partial(self) -> None:
        preds = [
            {"id": "g1", "predicted_tools": ["financial_lookup"]},
            {"id": "g3", "predicted_tools": []},  # doc_search 미호출
        ]
        assert number_accuracy(preds, self.GOLD) == pytest.approx(0.0)
        assert routing_accuracy(preds, self.GOLD) == pytest.approx(0.5)


# ── 결정론 도구 슬라이스 ──────────────────────────────────────────────────────
class TestLookupSlice:
    """픽스처 jsonl의 lookup/edge 항목을 모킹된 DART 페이로드로 검증."""

    def _run_lookup(self, item: dict) -> dict:
        payload = OFS_PAYLOAD if item.get("note", "").startswith("CFS 없는") else CFS_PAYLOAD
        with (
            patch("filing_agent.agent.tools._get_corp_code", return_value="00126380"),
            patch("filing_agent.agent.tools.fetch_single_account", return_value=payload),
        ):
            return financial_lookup.invoke({
                "company": item["company"],
                "account": item.get("account", "매출액"),  # 항목별 계정 사용
                "year": item["year"],
            })

    def test_all_lookup_items_match_expected(self) -> None:
        sample = load_jsonl(SAMPLE_JSONL)
        lookup_items = [
            it for it in sample
            if it["type"] in ("lookup", "edge") and it.get("expected_value") is not None
        ]
        assert lookup_items, "픽스처에 lookup/edge 항목이 없음"

        for item in lookup_items:
            result = self._run_lookup(item)
            assert result.get("found") is not False, (
                f"{item['id']}: financial_lookup이 found=False 반환 — 계정 조회 실패"
            )
            assert result["value"] == item["expected_value"], (
                f"{item['id']}: {result['value']} != {item['expected_value']}"
            )


class TestCalcSlice:
    """픽스처 jsonl의 calc 항목을 compute_change로 검증."""

    def test_calc_items_match_expected(self) -> None:
        sample = load_jsonl(SAMPLE_JSONL)
        calc_items = [
            it for it in sample
            if it["type"] == "calc" and it.get("expected_value") is not None
        ]
        assert calc_items, "픽스처에 calc 항목이 없음"

        for item in calc_items:
            with (
                patch("filing_agent.agent.tools._get_corp_code", return_value="00126380"),
                patch("filing_agent.agent.tools.fetch_single_account", return_value=CFS_PAYLOAD),
            ):
                result = compute_change.invoke({
                    "company": item["company"],
                    "account": item.get("account", "매출액"),
                    "year_from": item["year_from"],
                    "year_to": item["year_to"],
                })
            assert result.get("found") is not False, (
                f"{item['id']}: compute_change가 found=False 반환"
            )
            assert result["delta"] == item["expected_value"], (
                f"{item['id']}: delta {result['delta']} != {item['expected_value']}"
            )
