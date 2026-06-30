"""CLI 진입점 — 1명령으로 골든셋 점수표 출력.

사용법:
    python scripts/run_eval.py
    python scripts/run_eval.py --goldset eval/goldset.jsonl --out results/eval.json --k 5

키·DB·모델 필요(로컬 전용). CI에 포함하지 않는다.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# scripts/ → 프로젝트 루트를 sys.path에 추가(src 레이아웃 지원)
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def main() -> None:
    parser = argparse.ArgumentParser(description="골든셋 평가 실행")
    parser.add_argument("--goldset", default="eval/goldset.jsonl", help="골든셋 jsonl 경로")
    parser.add_argument("--out", default=None, help="결과 JSON 저장 경로(생략 시 콘솔만)")
    parser.add_argument("--k", type=int, default=5, help="Hit@k의 k 값")
    parser.add_argument(
        "--judge", action="store_true",
        help="서술형 답변을 LLM-judge로 추가 채점(보조 지표, 비결정론·키 필요)",
    )
    args = parser.parse_args()

    from filing_agent.agent.graph import get_graph
    from filing_agent.eval.metrics import aggregate, judge_aggregate
    from filing_agent.eval.runner import judge_predictions, run_goldset
    from filing_agent.eval.schema import load_jsonl
    from filing_agent.logging_config import configure_logging

    configure_logging()

    goldset_path = Path(args.goldset)
    if not goldset_path.exists():
        print(f"[오류] 골든셋 파일 없음: {goldset_path}", file=sys.stderr)
        sys.exit(1)

    gold = load_jsonl(goldset_path)
    print(f"골든셋 로드: {len(gold)}건")

    graph = get_graph()
    preds = run_goldset(graph, gold)
    print(f"예측 완료: {len(preds)}건")

    scores = aggregate(preds, gold, k=args.k)

    print("\n=== 평가 점수표 ===")
    print(f"  숫자 정답률  (number_accuracy)     : {scores['number_accuracy']:.3f}")
    print(f"  라우팅 정확도(routing_accuracy)    : {scores['routing_accuracy']:.3f}")
    sc = scores.get("scope_accuracy", 0.0)
    n_negative = scores.get("n_by_type", {}).get("negative", 0)
    scope_note = " ← 스코프 거부 미구현(알려진 갭)" if n_negative > 0 and sc < 1.0 else ""
    print(f"  스코프 거부  (scope_accuracy)      : {sc:.3f}{scope_note}")
    if f"hit@{args.k}" in scores:
        print(f"  Hit@{args.k}                          : {scores[f'hit@{args.k}']:.3f}")
        print(f"  MRR                                : {scores['mrr']:.3f}")
    print(f"  유형별 N     (n_by_type)           : {scores['n_by_type']}")
    print()
    print("* N이 작아 통계적 유의성 아님 — 개선 방향성 확인 용도.")

    judgements: list[dict] = []
    judge_scores: dict = {}
    if args.judge:
        print("\nLLM-judge 채점 중(서술형·하이브리드, 비결정론 보조 지표)...")
        judgements = judge_predictions(preds, gold)
        judge_scores = judge_aggregate(judgements)
        if judge_scores:
            print("\n--- 보조 지표 (LLM-judge · 비결정론 · 로컬 전용) ---")
            print(f"  faithfulness(근거 충실성): {judge_scores['faithfulness']:.3f}")
            print(f"  relevance(질문 적합성)   : {judge_scores['relevance']:.3f}")
            print(f"  채점 건수(n_judged)      : {judge_scores['n_judged']}")
        else:
            print("  (채점 대상 서술형 항목 없음)")

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"scores": scores, "predictions": preds}
        if args.judge:
            payload["judge_scores"] = judge_scores
            payload["judgements"] = judgements
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"\n결과 저장: {out_path}")


if __name__ == "__main__":
    main()
