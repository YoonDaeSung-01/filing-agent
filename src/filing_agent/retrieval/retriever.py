"""검색 파이프라인 — 벡터 + BM25 하이브리드 → RRF 융합 → cross-encoder 리랭킹.

흐름(Phase 2):
  1) 벡터: pgvector 코사인 유사도 top-N
  2) BM25: 메모리 인덱스(키워드)로 top-N  ← 회사명·숫자 정확 일치에 강함
  3) RRF: 두 랭킹을 Reciprocal Rank Fusion 으로 융합(점수 정규화 불필요)
  4) 리랭킹: cross-encoder 로 재정렬해 final_top_k

설정(config)으로 hybrid_enabled / rerank_enabled 를 끄면 각 단계를 건너뛴다.
BM25 인덱스는 전 코퍼스를 메모리에 1회 적재해 캐싱한다(데모 규모 14k 청크).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, TypedDict
from urllib.parse import urlparse

import numpy as np
import psycopg
from pgvector.psycopg import register_vector
from rank_bm25 import BM25Okapi

from filing_agent.config import Settings
from filing_agent.llm.client import embed
from filing_agent.retrieval.reranker import rerank


class RetrievedChunk(TypedDict):
    content: str
    source: str
    corp_name: str
    year: int
    score: float


# ── 토큰화 / RRF (순수 함수, DB·모델 불필요) ──────────────────────────────────

_TOKEN_RE = re.compile(r"[0-9a-z]+|[가-힣]+")


def _tokenize(text: str) -> list[str]:
    """소문자화 후 영숫자/한글 음절 런 단위로 토큰화한다.

    형태소 분석은 쓰지 않는다(의존성·속도). 회사명·숫자·영문 약어의
    정확 일치를 노리는 BM25 용도엔 충분하다. (형태소 분석은 추후 개선)
    """
    return _TOKEN_RE.findall(text.lower())


def _rrf_fuse(ranked_id_lists: list[list[int]], k: int) -> list[int]:
    """여러 랭킹(id 순서 리스트)을 Reciprocal Rank Fusion 으로 융합한다.

    score(id) = Σ 1 / (k + rank). rank 는 0부터. 점수 내림차순 id 리스트 반환.
    """
    scores: dict[int, float] = {}
    for ids in ranked_id_lists:
        for rank, doc_id in enumerate(ids):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores, key=lambda d: scores[d], reverse=True)


# ── DB 연결 ───────────────────────────────────────────────────────────────────

def _connect(settings: Settings) -> psycopg.Connection:
    p = urlparse(settings.pg_dsn)
    conn = psycopg.connect(
        host=p.hostname,
        port=p.port or 5432,
        dbname=(p.path or "").lstrip("/"),
        user=p.username,
        password=p.password,
        application_name="filing_agent",
    )
    register_vector(conn)
    return conn


def _match(doc: dict[str, Any], corp_name: str | None, year: int | None) -> bool:
    if corp_name is not None and doc["corp_name"] != corp_name:
        return False
    return not (year is not None and doc["year"] != year)


# ── 벡터 검색 ─────────────────────────────────────────────────────────────────

def _vector_search(
    query_vec: np.ndarray,
    settings: Settings,
    top_n: int,
    corp_name: str | None,
    year: int | None,
) -> list[dict[str, Any]]:
    where_parts: list[str] = []
    params: list[Any] = [query_vec]
    if corp_name is not None:
        where_parts.append("corp_name = %s")
        params.append(corp_name)
    if year is not None:
        where_parts.append("year = %s")
        params.append(year)
    where_clause = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""
    params += [query_vec, top_n]

    conn = _connect(settings)
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT id, content, source, corp_name, year,
                       (1 - (embedding <=> %s)) AS score
                FROM filing_chunks
                {where_clause}
                ORDER BY embedding <=> %s
                LIMIT %s
                """,
                params,
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    return [
        {
            "id": r[0],
            "content": r[1],
            "source": r[2],
            "corp_name": r[3],
            "year": r[4],
            "score": float(r[5]),
        }
        for r in rows
    ]


# ── BM25 검색 (메모리 인덱스 캐싱) ────────────────────────────────────────────

@dataclass
class _Bm25Index:
    bm25: BM25Okapi
    docs: list[dict[str, Any]]  # 토큰화 순서와 동일 정렬


_bm25_cache: dict[str, _Bm25Index] = {}


def reset_bm25_cache() -> None:
    """재인덱싱 후 메모리 BM25 인덱스를 무효화한다."""
    _bm25_cache.clear()


def _get_bm25_index(settings: Settings) -> _Bm25Index:
    key = settings.pg_dsn
    cached = _bm25_cache.get(key)
    if cached is not None:
        return cached

    conn = _connect(settings)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, content, source, corp_name, year FROM filing_chunks")
            rows = cur.fetchall()
    finally:
        conn.close()

    docs = [
        {"id": r[0], "content": r[1], "source": r[2], "corp_name": r[3], "year": r[4]}
        for r in rows
    ]
    tokenized = [_tokenize(d["content"]) for d in docs]
    index = _Bm25Index(bm25=BM25Okapi(tokenized), docs=docs)
    _bm25_cache[key] = index
    return index


def _bm25_search(
    query: str,
    settings: Settings,
    top_n: int,
    corp_name: str | None,
    year: int | None,
) -> list[dict[str, Any]]:
    index = _get_bm25_index(settings)
    if not index.docs:
        return []
    scores = index.bm25.get_scores(_tokenize(query))
    # 점수 내림차순 인덱스 → 메타데이터 필터 → top_n
    order = np.argsort(scores)[::-1]
    results: list[dict[str, Any]] = []
    for i in order:
        doc = index.docs[int(i)]
        if not _match(doc, corp_name, year):
            continue
        item = dict(doc)
        item["score"] = float(scores[int(i)])
        results.append(item)
        if len(results) >= top_n:
            break
    return results


# ── 공개 API ──────────────────────────────────────────────────────────────────

def search(
    query: str,
    settings: Settings,
    *,
    top_k: int | None = None,
    corp_name: str | None = None,
    year: int | None = None,
) -> list[RetrievedChunk]:
    """질문에 가장 관련 있는 청크를 검색·재정렬해 반환한다."""
    top_n = settings.retrieve_top_n
    final_k = top_k if top_k is not None else settings.final_top_k

    query_vec = np.array(embed([query], settings)[0], dtype=np.float32)
    vec_hits = _vector_search(query_vec, settings, top_n, corp_name, year)

    if settings.hybrid_enabled:
        bm25_hits = _bm25_search(query, settings, top_n, corp_name, year)
        by_id: dict[int, dict[str, Any]] = {h["id"]: h for h in bm25_hits}
        by_id.update({h["id"]: h for h in vec_hits})  # 벡터 메타 우선
        fused_ids = _rrf_fuse(
            [[h["id"] for h in vec_hits], [h["id"] for h in bm25_hits]],
            k=settings.rrf_k,
        )
        candidates = [by_id[i] for i in fused_ids][:top_n]
    else:
        candidates = vec_hits[:top_n]

    if settings.rerank_enabled and candidates:
        reranked = rerank(
            query, candidates, model_name=settings.rerank_model, top_n=final_k
        )
        return [_to_chunk(c, c.get("rerank_score", c.get("score", 0.0))) for c in reranked]

    return [_to_chunk(c, c.get("score", 0.0)) for c in candidates[:final_k]]


def _to_chunk(doc: dict[str, Any], score: float) -> RetrievedChunk:
    return RetrievedChunk(
        content=doc["content"],
        source=doc["source"],
        corp_name=doc["corp_name"],
        year=doc["year"],
        score=float(score),
    )
