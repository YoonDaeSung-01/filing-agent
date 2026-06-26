"""harness/verifier.py 단위 테스트 — 모델·DB·키 불필요."""

from filing_agent.harness.verifier import collect_fact_values, has_source, verify

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


class TestCollectFactValues:
    def test_lookup_value(self) -> None:
        assert 300_870_903_000_000 in collect_fact_values([LOOKUP_FACT])

    def test_change_all_values(self) -> None:
        vals = collect_fact_values([CHANGE_FACT])
        assert 258_935_494_000_000 in vals
        assert 300_870_903_000_000 in vals
        assert 41_935_409_000_000 in vals

    def test_skips_not_found(self) -> None:
        assert collect_fact_values([{"found": False, "reason": "x"}]) == set()


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

    def test_number_without_source_fails(self) -> None:
        figures = [{"account": "매출액", "year": 2024, "value": 300_870_903_000_000, "source": "x"}]
        ok, reason = verify(figures, [LOOKUP_FACT], "매출액은 300조원입니다")
        assert ok is False
        assert "출처" in reason

    def test_change_value_passes(self) -> None:
        figures = [{"account": "매출액", "year": 2024, "value": 41_935_409_000_000, "source": "x"}]
        ok, _ = verify(figures, [CHANGE_FACT], "증감액은 ...원입니다 (출처: 사업보고서)")
        assert ok is True

    def test_narrative_with_source_passes(self) -> None:
        ok, _ = verify([], [], "주요 사업 위험은 ... (출처: 2024 사업보고서 위험요인)")
        assert ok is True

    def test_narrative_without_source_fails(self) -> None:
        ok, reason = verify([], [], "주요 사업 위험은 환율 변동입니다")
        assert ok is False
        assert "출처" in reason
