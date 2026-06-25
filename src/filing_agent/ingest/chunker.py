"""텍스트 청킹 — 문단/문장 경계 존중 (Phase 2 고도화).

Phase 1 은 고정 크기 + overlap 으로 문장을 중간에서 잘랐다.
Phase 2 는 다음 우선순위로 경계를 존중해 의미 단위를 보존한다:
  1) 문단(빈 줄 또는 줄바꿈) 경계로 먼저 나눈다.
  2) 한 문단이 chunk_size 를 넘으면 문장 경계로 쪼갠다.
  3) 한 문장도 넘으면 마지막 수단으로 고정 크기 하드 분할.
인접 청크에 overlap(문자 수)을 주어 문맥 단절을 줄인다.

모든 청크는 len(content) <= chunk_size 를 보장한다.
"""

from __future__ import annotations

import re
from typing import TypedDict


class Chunk(TypedDict):
    content: str
    chunk_idx: int
    source: str
    corp_name: str
    year: int


# 한국어/영문 문장 종결: 마침표·물음표·느낌표 뒤 공백, 또는 "다." 류 종결.
_SENTENCE_END = re.compile(r"(?<=[.!?。])\s+|(?<=다\.)\s*")


def _split_paragraphs(text: str) -> list[str]:
    """빈 줄/줄바꿈 기준으로 문단을 나눈다. 빈 조각은 버린다."""
    parts = re.split(r"\n\s*\n|\n", text)
    return [p.strip() for p in parts if p.strip()]


def _split_sentences(paragraph: str) -> list[str]:
    """문단을 문장 단위로 나눈다."""
    parts = _SENTENCE_END.split(paragraph)
    return [s.strip() for s in parts if s.strip()]


def _hard_split(unit: str, chunk_size: int, overlap: int) -> list[str]:
    """경계가 없는 긴 조각을 stride(=chunk_size-overlap) 기반 슬라이딩으로 분할한다."""
    stride = max(1, chunk_size - overlap)
    return [unit[i : i + chunk_size] for i in range(0, len(unit), stride)]


def _emit_units(text: str, chunk_size: int, overlap: int) -> list[str]:
    """chunk_size 이하의 의미 단위(문단/문장/하드조각) 리스트를 만든다."""
    units: list[str] = []
    for para in _split_paragraphs(text):
        if len(para) <= chunk_size:
            units.append(para)
            continue
        for sent in _split_sentences(para):
            if len(sent) <= chunk_size:
                units.append(sent)
            else:
                units.extend(_hard_split(sent, chunk_size, overlap))
    return units


def chunk_text(
    text: str,
    *,
    corp_name: str,
    year: int,
    source: str,
    chunk_size: int = 500,
    overlap: int = 100,
) -> list[Chunk]:
    """경계를 존중해 텍스트를 청크로 나눈다.

    의미 단위(문단→문장→하드)를 chunk_size 까지 그리디로 묶고,
    청크 사이에 overlap 문자만큼 직전 꼬리를 이어 붙인다.
    """
    if not text:
        return []

    units = _emit_units(text, chunk_size, overlap)
    if not units:
        return []

    chunks: list[Chunk] = []
    idx = 0
    buf = ""

    def flush(content: str) -> None:
        nonlocal idx
        content = content.strip()
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

    for unit in units:
        if not buf:
            buf = unit
            continue
        # 한 칸 띄워 이어 붙였을 때 chunk_size 를 넘지 않으면 같은 청크로 묶는다.
        if len(buf) + 1 + len(unit) <= chunk_size:
            buf = f"{buf} {unit}"
        else:
            flush(buf)
            tail = buf[-overlap:] if overlap > 0 else ""
            # overlap 꼬리 + 새 unit 이 chunk_size 를 넘으면 꼬리는 버린다(불변식 유지).
            if tail and len(tail) + 1 + len(unit) <= chunk_size:
                buf = f"{tail} {unit}"
            else:
                buf = unit

    flush(buf)
    return chunks
