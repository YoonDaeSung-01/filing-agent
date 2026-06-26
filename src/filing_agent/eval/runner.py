"""골든셋 → 에이전트 실행 → 예측 수집.

로컬 전용(키·DB·모델 필요). CI에 포함하지 않는다.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _predicted_value(item_type: str, facts: list[dict]) -> int | None:
    """facts에서 예측값을 추출한다.

    - combine: 모든 value를 합산(LLM 산술 불신, 결정론 유지).
    - calc: delta 사용.
    - 그 외: 첫 번째 value.
    """
    if item_type == "calc":
        deltas = [f["delta"] for f in facts if isinstance(f.get("delta"), int)]
        return deltas[0] if deltas else None

    values = [f["value"] for f in facts if isinstance(f.get("value"), int)]
    if not values:
        return None
    return sum(values) if item_type == "combine" else values[0]


def _build_initial(item: dict[str, Any]) -> dict[str, Any]:
    """골든셋 항목에서 그래프 초기 상태를 만든다."""
    year = item.get("year") or item.get("year_to")
    return {
        "question": item["question"],
        "company": item.get("company"),
        "year": year,
        "messages": [],
        "tool_log": [],
        "steps": 0,
        "facts": [],
        "draft": None,
        "figures": [],
        "verifier_feedback": None,
        "verify_attempts": 0,
        "status": None,
        "answer": None,
        "sources": [],
    }


def run_goldset(graph: Any, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """골든셋을 에이전트로 실행하고 Prediction 리스트를 반환한다."""
    preds: list[dict[str, Any]] = []
    for item in items:
        item_id = item.get("id", "?")
        try:
            final = graph.invoke(_build_initial(item))
        except Exception as exc:  # noqa: BLE001
            logger.error("항목 %s 실행 실패: %s", item_id, exc)
            preds.append({
                "id": item_id,
                "type": item.get("type", "unknown"),
                "predicted_tools": [],
                "predicted_value": None,
                "answer": f"[오류] {exc}",
            })
            continue

        tool_log: list[dict] = final.get("tool_log") or []
        facts: list[dict] = final.get("facts") or []
        preds.append({
            "id": item_id,
            "type": item.get("type", "unknown"),
            "predicted_tools": [lg["tool"] for lg in tool_log if lg.get("ok")],
            "predicted_value": _predicted_value(item.get("type", ""), facts),
            "answer": final.get("answer") or "",
        })
        logger.info("항목 %s 완료: %s", item_id, preds[-1].get("predicted_value"))
    return preds
