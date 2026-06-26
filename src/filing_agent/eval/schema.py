"""골든셋·예측 레코드 스키마 + jsonl 로더."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class GoldItem(dict):
    """골든셋 레코드 타입(TypedDict 대용 — 선택 필드가 많아 dict 서브클래스로 표현)."""
    # id: str
    # type: str          — lookup | calc | routing | combine | hybrid | edge
    # question: str
    # company: str|None
    # year: int|None     — lookup/routing/hybrid/edge
    # year_from: int|None — calc
    # year_to: int|None  — calc
    # expected_value: int|None   — 수치 정답(미확정=None)
    # expected_tools: list[str]  — 라우팅 정답 도구 집합
    # relevant_company: str|None — Hit@k/MRR 출처 대조
    # relevant_year: int|None
    # note: str                  — edge 유형 비고


class Prediction(dict):
    """에이전트 실행 결과 레코드."""
    # id: str
    # type: str
    # predicted_tools: list[str]  — tool_log에서 ok==True인 도구명
    # predicted_value: int|None   — facts에서 추출
    # answer: str


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    """jsonl 파일을 한 줄씩 파싱해 dict 리스트로 반환한다."""
    records: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped:
                records.append(json.loads(stripped))
    return records
