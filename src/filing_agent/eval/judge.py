"""(선택) LLM-as-judge 어댑터 — 서술형 답변 보조 지표.

키 있을 때만 수동 실행. CI 비포함.
점수: 1(공시 근거·출처 있음) / 0(근거 없거나 출처 없음).
"""

from __future__ import annotations

import logging

import litellm

from filing_agent.config import get_settings
from filing_agent.llm.client import _with_retry

logger = logging.getLogger(__name__)

_PROMPT = (
    "다음 질문과 답변을 보고 채점하세요.\n"
    "기준: 공시 자료에 근거가 있고 출처가 명시됐으면 1, 아니면 0.\n"
    "응답은 숫자 0 또는 1만 반환하세요.\n\n"
    "질문: {question}\n답변: {answer}"
)


def judge_answer(question: str, answer: str) -> int:
    """LLM-judge로 답변을 채점한다. 반환값: 0 또는 1."""
    cfg = get_settings()
    prompt = _PROMPT.format(question=question, answer=answer)
    resp = _with_retry(
        lambda: litellm.completion(
            model=cfg.llm_model,
            messages=[{"role": "user", "content": prompt}],
            api_key=cfg.llm_api_key,
            max_tokens=10,
        ),
        what="LLM judge",
    )
    raw = (resp.choices[0].message.content or "").strip()
    score = 1 if raw.startswith("1") else 0
    logger.debug("judge: q=%s… score=%d", question[:30], score)
    return score


def batch_judge(preds: list[dict]) -> dict[str, int]:
    """예측 리스트를 judge해 {id: score} 딕셔너리를 반환한다."""
    return {
        p["id"]: judge_answer(p.get("question", ""), p.get("answer", ""))
        for p in preds
    }
