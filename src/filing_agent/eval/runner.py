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

    if item_type == "combine":
        # compute_sum 의 total 우선(도구가 결정론 합산). 없으면 개별 value 합산 폴백.
        totals = [f["total"] for f in facts if isinstance(f.get("total"), int)]
        if totals:
            return totals[0]
        values = [f["value"] for f in facts if isinstance(f.get("value"), int)]
        return sum(values) if values else None

    values = [f["value"] for f in facts if isinstance(f.get("value"), int)]
    return values[0] if values else None


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
        "doc_sources": [],
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


# judge 로 잴 유형 — 순수 서술(routing)만. 하이브리드 수치는 결정론(verifier)으로 검증되고,
# 수치+서술이 섞인 답변은 faithfulness 판정이 교란되므로 제외한다(보조 지표의 신뢰도 유지).
_NARRATIVE_TYPES = ("routing",)


def judge_predictions(
    preds: list[dict[str, Any]],
    items: list[dict[str, Any]],
    *,
    types: tuple[str, ...] = _NARRATIVE_TYPES,
) -> list[dict[str, Any]]:
    """서술형·하이브리드 답변을 LLM-judge로 채점한다(로컬 전용, 키·DB 필요).

    검색 컨텍스트는 retriever 를 직접 호출해 만든다(에이전트 우회 — Hit@k 와 같은 경로).
    Returns: [{id, faithfulness, relevance, reason}, ...]
    """
    from filing_agent.config import get_settings
    from filing_agent.eval.judge import judge_answer
    from filing_agent.retrieval.retriever import search

    cfg = get_settings()
    gold = {g["id"]: g for g in items}
    judgements: list[dict[str, Any]] = []
    for pred in preds:
        g = gold.get(pred["id"])
        if g is None or g.get("type") not in types:
            continue
        try:
            chunks = search(
                g["question"], cfg,
                corp_name=g.get("relevant_company"), year=g.get("relevant_year"),
            )
            context = "\n\n".join(c.get("content", "") for c in chunks[:5])
            verdict = judge_answer(g["question"], pred.get("answer", ""), context=context)
        except Exception as exc:  # noqa: BLE001
            logger.error("judge 항목 %s 실패: %s", pred["id"], exc)
            verdict = {"faithfulness": 0, "relevance": 0, "reason": f"[오류] {exc}"}
        judgements.append({"id": pred["id"], **verdict})
        logger.info("judge %s: %s", pred["id"], verdict)
    return judgements
