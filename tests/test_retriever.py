"""검색 파이프라인 순수 함수 테스트 — DB/모델 불필요.

토큰화·RRF 융합 로직만 검증한다. 벡터/BM25 인덱스·리랭킹은
실제 DB·모델이 필요하므로 수동(통합) 확인.
"""

from filing_agent.retrieval.retriever import _rrf_fuse, _tokenize


def test_tokenize_keeps_korean_latin_digits() -> None:
    toks = _tokenize("삼성전자 SK하이닉스 2024년 매출 300조")
    assert "삼성전자" in toks
    assert "sk" in toks          # 소문자화
    assert "하이닉스" in toks
    assert "2024" in toks
    assert "300" in toks


def test_tokenize_empty() -> None:
    assert _tokenize("") == []


def test_rrf_fuse_rewards_agreement() -> None:
    # 두 랭킹 모두에서 상위인 문서가 가장 앞으로 온다.
    vec_rank = [10, 20, 30]
    bm25_rank = [20, 40, 10]
    fused = _rrf_fuse([vec_rank, bm25_rank], k=60)
    # 20: 두 리스트에서 모두 상위(0위, 1위) → 1등이어야 한다.
    assert fused[0] == 20
    # 결과는 등장한 모든 id 의 합집합
    assert set(fused) == {10, 20, 30, 40}


def test_rrf_fuse_single_list_preserves_order() -> None:
    fused = _rrf_fuse([[1, 2, 3]], k=60)
    assert fused == [1, 2, 3]


def test_rrf_fuse_empty() -> None:
    assert _rrf_fuse([], k=60) == []
