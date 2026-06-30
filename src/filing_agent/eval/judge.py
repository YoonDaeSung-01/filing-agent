"""LLM-as-judge — 서술형 답변의 보조 품질 지표(faithfulness · relevance).

⚠️ 보조 지표다. 결정론 지표(숫자 정답률·라우팅·Hit@k)가 전면이고, judge 는 서술형 답변처럼
결정론으로 못 재는 부분만 보조로 잰다. 비결정론·키 필요·비용 → **로컬 전용, CI 비포함**.

채점 기준(검색 컨텍스트에 대조):
- faithfulness: 답변의 주장이 제공된 컨텍스트에 근거하면 1, 컨텍스트에 없는 내용을 지어냈으면 0.
- relevance:   답변이 질문에 실제로 답하면 1, 빗나가면 0.

파싱(_parse_verdict)은 순수 함수라 키 없이 테스트된다.
"""

from __future__ import annotations

import json
import logging
import re

import litellm

from filing_agent.config import get_settings
from filing_agent.llm.client import _with_retry

logger = logging.getLogger(__name__)

_PROMPT = (
    "당신은 RAG 답변 채점관입니다. 아래 [컨텍스트]만을 근거로 [답변]을 엄격히 채점하세요.\n"
    "- faithfulness: 답변의 모든 사실 주장이 [컨텍스트]에 근거하면 1, "
    "컨텍스트에 없는 내용을 지어냈으면 0.\n"
    "- relevance: 답변이 [질문]에 실제로 답하면 1, 빗나가거나 회피하면 0.\n"
    'JSON만 출력하세요: {{"faithfulness": 0|1, "relevance": 0|1, "reason": "한 문장"}}\n\n'
    "[질문]\n{question}\n\n[컨텍스트]\n{context}\n\n[답변]\n{answer}"
)

_DEFAULT_VERDICT = {"faithfulness": 0, "relevance": 0, "reason": "판정 파싱 실패"}


def _coerce01(v: object) -> int:
    """0/1 로 강제. 1 이상이거나 true 면 1, 그 외 0."""
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, (int, float)):
        return 1 if v >= 1 else 0
    if isinstance(v, str) and v.strip()[:1] in ("1", "t", "T", "y", "Y"):
        return 1
    return 0


def _parse_verdict(raw: str) -> dict:
    """judge 응답 텍스트에서 {faithfulness, relevance, reason} 를 robust 하게 추출한다."""
    if not raw:
        return dict(_DEFAULT_VERDICT)
    # 코드펜스/잡텍스트 안의 첫 JSON 오브젝트만 뽑는다.
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            return {
                "faithfulness": _coerce01(data.get("faithfulness")),
                "relevance": _coerce01(data.get("relevance")),
                "reason": str(data.get("reason", ""))[:200],
            }
        except (json.JSONDecodeError, AttributeError):
            pass
    return dict(_DEFAULT_VERDICT)


def judge_answer(question: str, answer: str, context: str = "") -> dict:
    """서술형 답변을 LLM-judge로 채점한다(로컬 전용, 키 필요).

    Returns: {faithfulness: 0|1, relevance: 0|1, reason: str}
    """
    cfg = get_settings()
    prompt = _PROMPT.format(question=question, context=context or "(컨텍스트 없음)", answer=answer)
    resp = _with_retry(
        lambda: litellm.completion(
            model=cfg.llm_model,
            messages=[{"role": "user", "content": prompt}],
            api_key=cfg.llm_api_key,
            max_tokens=200,
        ),
        what="LLM judge",
    )
    raw = (resp.choices[0].message.content or "").strip()
    verdict = _parse_verdict(raw)
    logger.debug("judge: q=%s… verdict=%s", question[:30], verdict)
    return verdict
