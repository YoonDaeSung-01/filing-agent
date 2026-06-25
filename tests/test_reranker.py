"""리랭커 단위 테스트 — 모델/torch 불필요(순수 정렬 로직만 검증)."""

from filing_agent.retrieval.reranker import _attach_and_sort


def _cands() -> list[dict]:
    return [
        {"content": "A", "source": "s1"},
        {"content": "B", "source": "s2"},
        {"content": "C", "source": "s3"},
    ]


def test_attach_and_sort_orders_by_score_desc() -> None:
    # 점수가 낮은→높은 순으로 들어와도 내림차순으로 재정렬된다.
    result = _attach_and_sort(_cands(), scores=[0.1, 0.9, 0.5], top_n=3)
    assert [c["content"] for c in result] == ["B", "C", "A"]
    assert result[0]["rerank_score"] == 0.9


def test_attach_and_sort_truncates_to_top_n() -> None:
    result = _attach_and_sort(_cands(), scores=[0.1, 0.9, 0.5], top_n=2)
    assert len(result) == 2
    assert [c["content"] for c in result] == ["B", "C"]


def test_attach_and_sort_preserves_metadata() -> None:
    result = _attach_and_sort(_cands(), scores=[0.1, 0.9, 0.5], top_n=1)
    assert result[0]["source"] == "s2"
    assert "rerank_score" in result[0]
