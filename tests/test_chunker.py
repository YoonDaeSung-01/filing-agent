"""청커 단위 테스트 — 네트워크/키 불필요."""

from filing_agent.ingest.chunker import chunk_text


def test_chunk_splits_long_text() -> None:
    text = "가나다라마" * 300  # 1500자
    chunks = chunk_text(
        text, corp_name="테스트", year=2024, source="test", chunk_size=200, overlap=50
    )
    assert len(chunks) >= 7
    for c in chunks:
        assert len(c["content"]) <= 200


def test_chunk_preserves_metadata() -> None:
    chunks = chunk_text("안녕하세요 반갑습니다", corp_name="삼성전자", year=2024, source="출처A")
    assert len(chunks) == 1
    assert chunks[0]["corp_name"] == "삼성전자"
    assert chunks[0]["year"] == 2024
    assert chunks[0]["source"] == "출처A"
    assert chunks[0]["chunk_idx"] == 0


def test_chunk_empty_text_returns_empty() -> None:
    assert chunk_text("", corp_name="A", year=2024, source="B") == []


def test_chunk_overlap_produces_extra_chunks() -> None:
    # overlap 이 있으면 순수 분할보다 청크 수가 많아진다
    text = "X" * 1000
    no_overlap = chunk_text(text, corp_name="A", year=2024, source="s", chunk_size=200, overlap=0)
    with_overlap = chunk_text(
        text, corp_name="A", year=2024, source="s", chunk_size=200, overlap=50
    )
    assert len(with_overlap) > len(no_overlap)
