"""harness/verifier.py 단위 테스트 — 모델·DB·키 불필요."""

from filing_agent.harness.verifier import (
    collect_fact_values,
    facts_have_source,
    has_source,
    verify,
)

# ── 픽스처: facts 예시 ───────────────────────────────────────────────────────
LOOKUP_FACT = {
    "company": "삼성전자",
    "account": "매출액",
    "year": 2024,
    "value": 300_870_903_000_000,
    "fs_div": "CFS",
    "source": "OpenDART fnlttSinglAcnt.json (...)",
}

CHANGE_FACT = {
    "company": "삼성전자",
    "account": "매출액",
    "year_from": 2023,
    "value_from": 258_935_494_000_000,
    "year_to": 2024,
    "value_to": 300_870_903_000_000,
    "delta": 41_935_409_000_000,
    "pct_change": 16.2,
    "fs_div": "CFS",
    "source": "OpenDART fnlttSinglAcnt.json (...)",
}


SUM_FACT = {
    "companies": ["삼성전자", "SK하이닉스"],
    "account": "매출액",
    "year": 2024,
    "values": [
        {"company": "삼성전자", "value": 300_870_903_000_000},
        {"company": "SK하이닉스", "value": 66_193_000_000_000},
    ],
    "total": 367_063_903_000_000,
    "fs_div": "CFS",
    "source": ["OpenDART (...삼성)", "OpenDART (...SK)"],
}


class TestCollectFactValues:
    def test_lookup_value(self) -> None:
        assert 300_870_903_000_000 in collect_fact_values([LOOKUP_FACT])

    def test_change_all_values(self) -> None:
        vals = collect_fact_values([CHANGE_FACT])
        assert 258_935_494_000_000 in vals
        assert 300_870_903_000_000 in vals
        assert 41_935_409_000_000 in vals

    def test_sum_total_and_individuals(self) -> None:
        vals = collect_fact_values([SUM_FACT])
        assert 367_063_903_000_000 in vals  # total
        assert 300_870_903_000_000 in vals  # 개별
        assert 66_193_000_000_000 in vals   # 개별

    def test_skips_not_found(self) -> None:
        assert collect_fact_values([{"found": False, "reason": "x"}]) == set()


class TestFactsHaveSource:
    def test_present(self) -> None:
        assert facts_have_source([LOOKUP_FACT]) is True

    def test_empty_source_is_false(self) -> None:
        assert facts_have_source([{**LOOKUP_FACT, "source": ""}]) is False

    def test_skips_not_found(self) -> None:
        assert facts_have_source([{"found": False, "source": "x"}]) is False

    def test_empty_facts(self) -> None:
        assert facts_have_source([]) is False


class TestHasSource:
    def test_present(self) -> None:
        assert has_source("삼성전자 2024년 매출액은 ... (출처: 사업보고서)")

    def test_absent(self) -> None:
        assert not has_source("그냥 숫자만 있는 답변 300870903000000원")

    def test_empty(self) -> None:
        assert not has_source("")


class TestVerify:
    def test_correct_number_with_source_passes(self) -> None:
        figures = [{"account": "매출액", "year": 2024, "value": 300_870_903_000_000, "source": "x"}]
        ok, reason = verify(figures, [LOOKUP_FACT], "매출액은 ...원입니다 (출처: 사업보고서)")
        assert ok is True
        assert reason == ""

    def test_hallucinated_number_fails(self) -> None:
        figures = [{"account": "매출액", "year": 2024, "value": 999_999_999, "source": "x"}]
        ok, reason = verify(figures, [LOOKUP_FACT], "매출액은 ...원 (출처: 보고서)")
        assert ok is False
        assert "일치하지 않" in reason

    def test_number_without_facts_fails(self) -> None:
        figures = [{"account": "매출액", "year": 2024, "value": 300_870_903_000_000, "source": "x"}]
        ok, reason = verify(figures, [], "매출액은 ...원 (출처: 보고서)")
        assert ok is False
        assert "조회된 재무 값" in reason

    def test_number_passes_when_fact_has_source_without_prose_marker(self) -> None:
        # structured output 에선 출처가 facts.source 에 있으므로 산문 마커가 없어도 통과해야 한다.
        figures = [{"account": "매출액", "year": 2024, "value": 300_870_903_000_000, "source": "x"}]
        ok, reason = verify(figures, [LOOKUP_FACT], "매출액은 300조원입니다")
        assert ok is True
        assert reason == ""

    def test_number_fails_when_no_source_anywhere(self) -> None:
        # facts 에도 source 가 없고 산문에도 표지가 없으면 실패.
        fact_no_source = {**LOOKUP_FACT, "source": ""}
        figures = [{"account": "매출액", "year": 2024, "value": 300_870_903_000_000, "source": "x"}]
        ok, reason = verify(figures, [fact_no_source], "매출액은 300조원입니다")
        assert ok is False
        assert "출처" in reason

    def test_change_value_passes(self) -> None:
        figures = [{"account": "매출액", "year": 2024, "value": 41_935_409_000_000, "source": "x"}]
        ok, _ = verify(figures, [CHANGE_FACT], "증감액은 ...원입니다 (출처: 사업보고서)")
        assert ok is True

    def test_sum_total_passes(self) -> None:
        figures = [{"account": "매출액", "year": 2024,
                    "value": 367_063_903_000_000, "source": "x"}]
        ok, _ = verify(figures, [SUM_FACT], "합계는 ...원입니다 (출처: 공시)")
        assert ok is True

    def test_narrative_with_source_passes(self) -> None:
        ok, _ = verify([], [], "주요 사업 위험은 ... (출처: 2024 사업보고서 위험요인)")
        assert ok is True

    def test_narrative_without_source_fails(self) -> None:
        ok, reason = verify([], [], "주요 사업 위험은 환율 변동입니다")
        assert ok is False
        assert "출처" in reason
