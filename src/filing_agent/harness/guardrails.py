"""가드레일 — 입력/출력 검증(규칙 기반, LLM 호출 없음).

입력: 프롬프트 인젝션 차단 · 길이 제한 · 투자조언 선회.
출력: 출처 표지 검사(가벼운 최종 점검).

규칙 기반이라 결정론적이고 순수 함수로 테스트된다.
"""

from __future__ import annotations

import re
from typing import Literal, TypedDict

# ── 입력 가드 ────────────────────────────────────────────────────────────────

# 프롬프트 인젝션 패턴(대소문자 무시)
_INJECTION_PATTERNS = [
    r"이전\s*지시.*무시",
    r"위\s*지시.*무시",
    r"앞서.*지시.*무시",
    r"ignore\s+(all\s+)?previous",
    r"ignore\s+(the\s+)?above",
    r"disregard\s+(all\s+)?previous",
    r"system\s*prompt",
    r"시스템\s*프롬프트",
    r"너의?\s*지시문",
    r"규칙을?\s*무시",
]

# 투자조언 요청 패턴 → 차단이 아니라 사실 추출로 선회
_INVESTMENT_PATTERNS = [
    r"사야\s*(하나|할까|돼|됩니까|해)",
    r"팔아야\s*(하나|할까|돼|됩니까|해)",
    r"매수\s*(추천|할까|하나|해야)",
    r"매도\s*(추천|할까|하나|해야)",
    r"투자\s*(해야|할까|추천|가치)",
    r"오를까|내릴까|떨어질까|전망\s*어때",
    r"사도\s*(돼|될까|괜찮)",
]

_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)
_INVESTMENT_RE = re.compile("|".join(_INVESTMENT_PATTERNS))

_INJECTION_MSG = "요청을 처리할 수 없습니다. 이 도구는 공시된 사실을 추출·계산하는 용도입니다."
_INVESTMENT_MSG = (
    "매수·매도 추천은 제공하지 않습니다. 이 도구는 투자 조언 도구가 아닙니다. "
    "대신 공시된 실적·재무 사실(매출·이익·자산 등)을 출처와 함께 알려드릴 수 있습니다."
)


class GuardResult(TypedDict):
    action: Literal["pass", "block"]
    answer: str  # block 일 때 사용자에게 보낼 안내문(pass 면 빈 문자열)


def check_input(question: str, *, max_chars: int = 2000) -> GuardResult:
    """입력 가드. 통과면 pass, 차단/선회면 block + 안내문."""
    if not question or not question.strip():
        return {"action": "block", "answer": "질문이 비어 있습니다."}
    if len(question) > max_chars:
        return {"action": "block", "answer": f"질문이 너무 깁니다(최대 {max_chars}자)."}
    if _INJECTION_RE.search(question):
        return {"action": "block", "answer": _INJECTION_MSG}
    if _INVESTMENT_RE.search(question):
        return {"action": "block", "answer": _INVESTMENT_MSG}
    return {"action": "pass", "answer": ""}


# ── 출력 가드 ────────────────────────────────────────────────────────────────

def check_output(answer: str, *, has_figures: bool, has_sources: bool = False) -> GuardResult:
    """출력 가드. 수치 답변인데 출처가 어디에도 없으면 경고를 덧붙인다(차단까진 아님).

    출처는 산문 표지 또는 구조화된 sources(has_sources) 중 하나면 충족으로 본다
    (verifier 와 동일한 기준 — structured output 의 출처는 sources 리스트에 담긴다).
    """
    if has_figures and not has_sources and not _has_source_marker(answer):
        return {
            "action": "block",
            "answer": answer + "\n\n⚠️ (주의: 이 답변의 출처가 명시되지 않았습니다.)",
        }
    return {"action": "pass", "answer": answer}


def _has_source_marker(text: str) -> bool:
    return any(m in text for m in ("출처", "보고서", "OpenDART", "공시"))
