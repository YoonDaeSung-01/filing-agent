"""Cross-encoder 리랭킹 — BGE-reranker-v2-m3 (Phase 2).

검색 1단계(벡터/BM25)는 재현율(많이 가져오기)에 강하지만 정밀도가 낮다.
cross-encoder 는 (질문, 청크) 쌍을 함께 인코딩해 관련도를 직접 점수화하므로
top-N 후보를 받아 재정렬하면 상위 정밀도가 크게 오른다.

모델은 무겁고 torch 를 요구하므로 **최초 호출 시에만 lazy 로딩**한다.
모듈 import 자체는 torch 없이도 되어, 모델 없는 환경에서 테스트가 통과한다.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

# 모델 인스턴스는 프로세스 내 1회만 로딩(캐시).


@lru_cache(maxsize=2)
def _get_reranker(model_name: str) -> Any:
    """CrossEncoder 를 lazy 로딩한다. torch/sentence-transformers 가 이 시점에만 필요.

    (FlagEmbedding 의 FlagReranker 는 transformers 5.x 와 비호환이라 CrossEncoder 사용.)
    """
    from sentence_transformers import CrossEncoder

    return CrossEncoder(model_name)


def _attach_and_sort(
    candidates: list[dict[str, Any]],
    scores: list[float],
    top_n: int,
) -> list[dict[str, Any]]:
    """점수를 'rerank_score' 로 붙이고 내림차순 정렬 후 상위 top_n 을 반환한다.

    모델 없이도 검증 가능한 순수 함수(테스트 대상).
    """
    scored = []
    for cand, score in zip(candidates, scores, strict=True):
        item = dict(cand)
        item["rerank_score"] = float(score)
        scored.append(item)
    scored.sort(key=lambda c: c["rerank_score"], reverse=True)
    return scored[:top_n]


def rerank(
    query: str,
    candidates: list[dict[str, Any]],
    *,
    model_name: str,
    top_n: int,
) -> list[dict[str, Any]]:
    """후보 청크를 cross-encoder 로 재정렬해 상위 top_n 을 반환한다."""
    if not candidates:
        return []

    reranker = _get_reranker(model_name)
    pairs = [[query, c.get("content", "")] for c in candidates]
    scores = reranker.predict(pairs)  # numpy 배열(로짓). 순위는 단조라 정렬에 충분.
    return _attach_and_sort(candidates, list(scores), top_n)
