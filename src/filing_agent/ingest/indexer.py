"""공시 텍스트 청크 임베딩 → pgvector 저장.

테이블 스키마:
  filing_chunks(id, corp_name, year, source, content, embedding, chunk_idx)

인덱스: HNSW (동적 삽입에 적합, IVFFlat 보다 빌드 시 데이터 필요 없음)
"""

from __future__ import annotations

import numpy as np
import psycopg2
from pgvector.psycopg2 import register_vector

from filing_agent.config import Settings
from filing_agent.ingest.chunker import Chunk
from filing_agent.llm.client import embed

_DDL = """
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS filing_chunks (
    id          BIGSERIAL PRIMARY KEY,
    corp_name   TEXT    NOT NULL,
    year        INTEGER NOT NULL,
    source      TEXT    NOT NULL,
    content     TEXT    NOT NULL,
    embedding   VECTOR({dim}) NOT NULL,
    chunk_idx   INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS filing_chunks_emb_idx
    ON filing_chunks USING hnsw (embedding vector_cosine_ops);
"""


def _conn(settings: Settings):
    conn = psycopg2.connect(settings.pg_dsn)
    register_vector(conn)
    return conn


def setup_table(settings: Settings) -> None:
    """테이블과 HNSW 인덱스를 생성한다(멱등)."""
    ddl = _DDL.format(dim=settings.embedding_dim)
    with _conn(settings) as conn, conn.cursor() as cur:
        cur.execute(ddl)
        conn.commit()


def index_chunks(
    chunks: list[Chunk],
    settings: Settings,
    batch_size: int = 50,
) -> int:
    """청크를 임베딩 후 pgvector 에 저장한다. 저장된 청크 수를 반환한다."""
    if not chunks:
        return 0

    stored = 0
    with _conn(settings) as conn, conn.cursor() as cur:
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            vectors = embed([c["content"] for c in batch], settings)
            for chunk, vec in zip(batch, vectors, strict=True):
                cur.execute(
                    """
                    INSERT INTO filing_chunks
                        (corp_name, year, source, content, embedding, chunk_idx)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        chunk["corp_name"],
                        chunk["year"],
                        chunk["source"],
                        chunk["content"],
                        np.array(vec, dtype=np.float32),
                        chunk["chunk_idx"],
                    ),
                )
                stored += 1
        conn.commit()
    return stored


def clear_corp_year(corp_name: str, year: int, settings: Settings) -> None:
    """재인덱싱 전 기존 청크를 삭제한다."""
    with _conn(settings) as conn, conn.cursor() as cur:
        cur.execute(
            "DELETE FROM filing_chunks WHERE corp_name = %s AND year = %s",
            (corp_name, year),
        )
        conn.commit()
