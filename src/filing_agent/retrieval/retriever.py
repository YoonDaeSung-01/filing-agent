"""pgvector 기반 코사인 유사도 검색."""

from __future__ import annotations

from typing import TypedDict

import numpy as np
import psycopg2
from pgvector.psycopg2 import register_vector

from filing_agent.config import Settings
from filing_agent.llm.client import embed


class RetrievedChunk(TypedDict):
    content: str
    source: str
    corp_name: str
    year: int
    score: float


def search(
    query: str,
    settings: Settings,
    *,
    top_k: int = 5,
    corp_name: str | None = None,
    year: int | None = None,
) -> list[RetrievedChunk]:
    """질문과 코사인 유사도가 높은 청크 top_k 개를 반환한다."""
    query_vec = np.array(embed([query], settings)[0], dtype=np.float32)

    conn = psycopg2.connect(settings.pg_dsn)
    register_vector(conn)
    try:
        with conn.cursor() as cur:
            where_parts: list[str] = []
            params: list = [query_vec]

            if corp_name is not None:
                where_parts.append("corp_name = %s")
                params.append(corp_name)
            if year is not None:
                where_parts.append("year = %s")
                params.append(year)

            where_clause = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""
            params += [query_vec, top_k]

            cur.execute(
                f"""
                SELECT content, source, corp_name, year,
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
        RetrievedChunk(
            content=row[0],
            source=row[1],
            corp_name=row[2],
            year=row[3],
            score=float(row[4]),
        )
        for row in rows
    ]
