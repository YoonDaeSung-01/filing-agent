"""평가 지표 — 순수 함수(키·모델·DB 불필요, CI에서 단위 테스트 가능).

모든 함수는 이미 수집된 예측/정답을 입력받아 점수를 반환한다.
숫자 대조는 결정론적(정수 동일성), 라우팅 대조는 집합 포함 관계로 판단한다.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any


def number_accuracy(preds: list[dict], gold: list[dict]) -> float:
    """type∈{lookup,calc,combine,edge}이고 expected_value가 확정된 항목의 정답률."""
    numeric_types = {"lookup", "calc", "combine", "edge"}
    gold_map = {g["id"]: g for g in gold}
    total = correct = 0
    for pred in preds:
        g = gold_map.get(pred["id"])
        if g is None or g.get("type") not in numeric_types:
            continue
        expected = g.get("expected_value")
        if expected is None:
            continue  # 미확정 항목 분모 제외
        total += 1
        if pred.get("predicted_value") == expected:
            correct += 1
    return correct / total if total > 0 else 0.0


def routing_accuracy(preds: list[dict], gold: list[dict]) -> float:
    """예측 도구 집합이 expected_tools를 모두 포함하는 비율(superset 허용)."""
    gold_map = {g["id"]: g for g in gold}
    total = correct = 0
    for pred in preds:
        g = gold_map.get(pred["id"])
        if g is None:
            continue
        expected = set(g.get("expected_tools") or [])
        if not expected:
            continue
        total += 1
        predicted = set(pred.get("predicted_tools") or [])
        if expected.issubset(predicted):
            correct += 1
    return correct / total if total > 0 else 0.0


def hit_at_k(retrieved: list[tuple[str, int]], relevant: tuple[str, int], k: int) -> float:
    """top-k의 (corp_name, year) 중 relevant와 일치가 하나라도 있으면 1.0."""
    for corp, year in retrieved[:k]:
        if (corp, year) == relevant:
            return 1.0
    return 0.0


def mrr(retrieved: list[tuple[str, int]], relevant: tuple[str, int]) -> float:
    """첫 번째 relevant (corp_name, year) 일치의 역순위(1/rank). 없으면 0."""
    for rank, (corp, year) in enumerate(retrieved, 1):
        if (corp, year) == relevant:
            return 1.0 / rank
    return 0.0


def aggregate(
    preds: list[dict],
    gold: list[dict],
    retrievals: list[dict[str, Any]] | None = None,
    k: int = 5,
) -> dict[str, Any]:
    """전체 점수표를 계산해 반환한다.

    Returns:
        {number_accuracy, routing_accuracy, n_by_type,
         hit@k, mrr} (Hit@k·MRR는 retrievals 있을 때만)
    """
    result: dict[str, Any] = {
        "number_accuracy": number_accuracy(preds, gold),
        "routing_accuracy": routing_accuracy(preds, gold),
    }

    if retrievals:
        gold_map = {g["id"]: g for g in gold}
        hits, mrrs, n = [], [], 0
        for ret in retrievals:
            g = gold_map.get(ret.get("id"))
            if g is None:
                continue
            rc, ry = g.get("relevant_company"), g.get("relevant_year")
            if rc is None or ry is None:
                continue
            relevant = (rc, ry)
            chunks: list[dict] = ret.get("chunks", [])
            top_k = [(c["corp_name"], c["year"]) for c in chunks]
            hits.append(hit_at_k(top_k, relevant, k))
            mrrs.append(mrr(top_k, relevant))
            n += 1
        result[f"hit@{k}"] = sum(hits) / n if n > 0 else 0.0
        result["mrr"] = sum(mrrs) / n if n > 0 else 0.0

    gold_map = {g["id"]: g for g in gold}
    n_by_type: dict[str, int] = defaultdict(int)
    for pred in preds:
        g = gold_map.get(pred["id"])
        if g:
            n_by_type[g.get("type", "unknown")] += 1
    result["n_by_type"] = dict(n_by_type)

    return result
