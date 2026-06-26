"""eval/metrics.py 채점 함수 단위 테스트 — 키·모델·DB 불필요."""

import pytest

from filing_agent.eval.metrics import (
    aggregate,
    hit_at_k,
    mrr,
    number_accuracy,
    routing_accuracy,
)

# ── 샘플 골든셋 ──────────────────────────────────────────────────────────────
GOLD = [
    {
        "id": "q1", "type": "lookup",
        "expected_value": 300_870_903_000_000,
        "expected_tools": ["financial_lookup"],
        "relevant_company": "삼성전자", "relevant_year": 2024,
    },
    {
        "id": "q2", "type": "calc",
        "expected_value": 41_935_409_000_000,
        "expected_tools": ["compute_change"],
        "relevant_company": "삼성전자", "relevant_year": 2024,
    },
    {
        "id": "q3", "type": "routing",
        "expected_value": None,
        "expected_tools": ["doc_search"],
        "relevant_company": "삼성전자", "relevant_year": 2024,
    },
    {
        "id": "q4", "type": "hybrid",
        "expected_value": None,
        "expected_tools": ["financial_lookup", "doc_search"],
        "relevant_company": "삼성전자", "relevant_year": 2024,
    },
    {
        "id": "q5", "type": "edge",
        "expected_value": 200,
        "expected_tools": ["financial_lookup"],
        "relevant_company": "테스트", "relevant_year": 2023,
    },
]


# ── number_accuracy ──────────────────────────────────────────────────────────
class TestNumberAccuracy:
    def test_all_correct(self) -> None:
        preds = [
            {"id": "q1", "predicted_value": 300_870_903_000_000},
            {"id": "q2", "predicted_value": 41_935_409_000_000},
            {"id": "q5", "predicted_value": 200},
        ]
        assert number_accuracy(preds, GOLD) == 1.0

    def test_partial_correct(self) -> None:
        preds = [
            {"id": "q1", "predicted_value": 300_870_903_000_000},
            {"id": "q2", "predicted_value": 0},  # 틀림
        ]
        assert number_accuracy(preds, GOLD) == pytest.approx(0.5)

    def test_none_expected_excluded_from_denominator(self) -> None:
        # expected_value=None인 항목은 분모·분자 모두 제외
        preds = [{"id": "q3", "predicted_value": 999}]
        assert number_accuracy(preds, GOLD) == 0.0  # total=0 → 0.0

    def test_routing_type_not_counted(self) -> None:
        preds = [
            {"id": "q1", "predicted_value": 300_870_903_000_000},
            {"id": "q3", "predicted_value": 999},  # routing 유형 — 제외
        ]
        assert number_accuracy(preds, GOLD) == 1.0  # q1만 분모

    def test_wrong_value_scores_zero(self) -> None:
        preds = [{"id": "q1", "predicted_value": 1}]
        assert number_accuracy(preds, GOLD) == 0.0

    def test_empty_preds(self) -> None:
        assert number_accuracy([], GOLD) == 0.0


# ── routing_accuracy ─────────────────────────────────────────────────────────
class TestRoutingAccuracy:
    def test_exact_match(self) -> None:
        preds = [{"id": "q1", "predicted_tools": ["financial_lookup"]}]
        assert routing_accuracy(preds, GOLD) == 1.0

    def test_superset_allowed(self) -> None:
        # 기대 도구 외에 추가 도구가 있어도 OK
        preds = [{"id": "q3", "predicted_tools": ["doc_search", "financial_lookup"]}]
        assert routing_accuracy(preds, GOLD) == 1.0

    def test_missing_one_tool_fails(self) -> None:
        preds = [{"id": "q4", "predicted_tools": ["financial_lookup"]}]  # doc_search 빠짐
        assert routing_accuracy(preds, GOLD) == 0.0

    def test_hybrid_both_required(self) -> None:
        preds = [{"id": "q4", "predicted_tools": ["financial_lookup", "doc_search"]}]
        assert routing_accuracy(preds, GOLD) == 1.0

    def test_empty_predicted_tools_fails(self) -> None:
        preds = [{"id": "q1", "predicted_tools": []}]
        assert routing_accuracy(preds, GOLD) == 0.0

    def test_empty_preds(self) -> None:
        assert routing_accuracy([], GOLD) == 0.0


# ── hit_at_k ─────────────────────────────────────────────────────────────────
class TestHitAtK:
    def test_hit_within_k(self) -> None:
        retrieved = [("LG전자", 2024), ("삼성전자", 2024), ("SK하이닉스", 2024)]
        assert hit_at_k(retrieved, ("삼성전자", 2024), k=5) == 1.0

    def test_hit_at_boundary(self) -> None:
        retrieved = [("A", 2024), ("B", 2024), ("삼성전자", 2024)]
        assert hit_at_k(retrieved, ("삼성전자", 2024), k=3) == 1.0

    def test_beyond_k_not_counted(self) -> None:
        retrieved = [("A", 2024), ("B", 2024), ("삼성전자", 2024)]
        assert hit_at_k(retrieved, ("삼성전자", 2024), k=2) == 0.0

    def test_empty_retrieved(self) -> None:
        assert hit_at_k([], ("삼성전자", 2024), k=5) == 0.0

    def test_year_mismatch_not_hit(self) -> None:
        retrieved = [("삼성전자", 2023)]
        assert hit_at_k(retrieved, ("삼성전자", 2024), k=5) == 0.0


# ── mrr ──────────────────────────────────────────────────────────────────────
class TestMRR:
    def test_rank_1(self) -> None:
        retrieved = [("삼성전자", 2024), ("LG전자", 2024)]
        assert mrr(retrieved, ("삼성전자", 2024)) == pytest.approx(1.0)

    def test_rank_2(self) -> None:
        retrieved = [("LG전자", 2024), ("삼성전자", 2024)]
        assert mrr(retrieved, ("삼성전자", 2024)) == pytest.approx(0.5)

    def test_rank_3(self) -> None:
        retrieved = [("A", 2024), ("B", 2024), ("삼성전자", 2024)]
        assert mrr(retrieved, ("삼성전자", 2024)) == pytest.approx(1 / 3)

    def test_not_found_returns_zero(self) -> None:
        retrieved = [("LG전자", 2024)]
        assert mrr(retrieved, ("삼성전자", 2024)) == 0.0

    def test_empty_returns_zero(self) -> None:
        assert mrr([], ("삼성전자", 2024)) == 0.0


# ── aggregate ────────────────────────────────────────────────────────────────
class TestAggregate:
    def test_scores_present(self) -> None:
        preds = [
            {"id": "q1", "predicted_value": 300_870_903_000_000,
             "predicted_tools": ["financial_lookup"]},
            {"id": "q5", "predicted_value": 200,
             "predicted_tools": ["financial_lookup"]},
        ]
        result = aggregate(preds, GOLD)
        assert result["number_accuracy"] == 1.0
        assert result["routing_accuracy"] == 1.0
        assert "n_by_type" in result
        assert "hit@5" not in result  # retrievals 없으면 미포함

    def test_n_by_type_counts(self) -> None:
        preds = [
            {"id": "q1", "predicted_value": 300_870_903_000_000, "predicted_tools": []},
            {"id": "q3", "predicted_value": None, "predicted_tools": ["doc_search"]},
        ]
        result = aggregate(preds, GOLD)
        assert result["n_by_type"].get("lookup") == 1
        assert result["n_by_type"].get("routing") == 1

    def test_with_retrievals_adds_hit_mrr(self) -> None:
        preds = [{"id": "q1", "predicted_value": 300_870_903_000_000,
                  "predicted_tools": ["financial_lookup"]}]
        retrievals = [
            {"id": "q1", "chunks": [{"corp_name": "삼성전자", "year": 2024}]}
        ]
        result = aggregate(preds, GOLD, retrievals=retrievals, k=5)
        assert result["hit@5"] == 1.0
        assert result["mrr"] == pytest.approx(1.0)

    def test_retrievals_miss(self) -> None:
        preds = [{"id": "q1", "predicted_value": 300_870_903_000_000,
                  "predicted_tools": ["financial_lookup"]}]
        retrievals = [
            {"id": "q1", "chunks": [{"corp_name": "LG전자", "year": 2024}]}
        ]
        result = aggregate(preds, GOLD, retrievals=retrievals, k=5)
        assert result["hit@5"] == 0.0
        assert result["mrr"] == 0.0
