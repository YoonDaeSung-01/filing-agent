"""텍스트 청킹 — 고정 크기 + overlap (Phase 1 기본 전략).

Phase 2 에서 문단/섹션 경계 존중 방식으로 고도화한다.
"""

from __future__ import annotations

from typing import TypedDict


class Chunk(TypedDict):
    content: str
    chunk_idx: int
    source: str
    corp_name: str
    year: int


def chunk_text(
    text: str,
    *,
    corp_name: str,
    year: int,
    source: str,
    chunk_size: int = 500,
    overlap: int = 100,
) -> list[Chunk]:
    """텍스트를 고정 크기(문자 수) + overlap 으로 나눈다."""
    if not text:
        return []

    chunks: list[Chunk] = []
    start = 0
    idx = 0
    while start < len(text):
        end = start + chunk_size
        content = text[start:end].strip()
        if content:
            chunks.append(
                Chunk(
                    content=content,
                    chunk_idx=idx,
                    source=source,
                    corp_name=corp_name,
                    year=year,
                )
            )
            idx += 1
        start += chunk_size - overlap
    return chunks
