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


def test_chunk_respects_sentence_boundaries() -> None:
    # 문장이 chunk_size 안에 들어가면 중간에서 잘리지 않고 통째로 보존된다.
    text = "삼성전자는 반도체를 만든다. 디스플레이도 만든다. 가전도 만든다."
    chunks = chunk_text(
        text, corp_name="삼성전자", year=2024, source="s", chunk_size=200, overlap=0
    )
    assert len(chunks) == 1
    # 모든 문장이 한 청크에 온전히 포함된다
    assert "반도체를 만든다." in chunks[0]["content"]
    assert "가전도 만든다." in chunks[0]["content"]


def test_chunk_packs_paragraphs_under_size() -> None:
    # 짧은 문단 여러 개를 chunk_size 까지 묶되, 각 청크는 chunk_size 를 넘지 않는다.
    paras = "\n\n".join(f"문단{i} " + "가" * 80 for i in range(6))
    chunks = chunk_text(
        paras, corp_name="A", year=2024, source="s", chunk_size=200, overlap=20
    )
    assert len(chunks) >= 2
    for c in chunks:
        assert len(c["content"]) <= 200
