"""루프 계약 — 에이전트의 목표·범위·종료 조건·예산을 한 곳에 명시.

plan.md Phase 4의 루프 계약을 코드로 표현한다. 실제 예산 값은 config(Settings)에서 읽고,
이 모듈은 '계약의 형태'(불변 메타데이터)를 문서화·노출한다.
"""

from __future__ import annotations

from typing import TypedDict


class LoopContract(TypedDict):
    goal: str
    scope: list[str]
    verifier: str
    stop_condition: str
    escalation: str


CONTRACT: LoopContract = {
    "goal": "공시 근거로 사실을 답한다(투자 조언 아님).",
    "scope": ["doc_search", "financial_lookup", "compute_change"],
    "verifier": (
        "숫자 답변은 조회된 실제 재무 값(facts)과 결정론적으로 대조하고 출처를 인용한다. "
        "서술 답변은 출처 표지가 1개 이상 있어야 한다."
    ),
    "stop_condition": "검증 통과(ok) 또는 tool 예산/검증 예산 도달.",
    "escalation": "예산 도달 시 우아한 실패 템플릿(부분 결과 + 다음 행동)으로 응답.",
}
