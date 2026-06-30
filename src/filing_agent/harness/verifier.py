"""검증 루프 — 답변 숫자를 조회값(facts)과 결정론적으로 대조한다.

LLM-judge 가 아니다. finalize 가 structured output 으로 낸 figures(주장 수치)의 value 를
state.facts 의 실제 조회값과 정수 대조한다. 순수 함수라 모델·DB·키 없이 테스트된다.

facts 의 형태(도구별):
- financial_lookup: {company, account, year, value, fs_div, source}
- compute_change:   {company, account, year_from, value_from, year_to, value_to,
                     delta, pct_change, fs_div, source}
→ 두 형태에서 나오는 모든 정수 수치를 모아 "허용 값 집합"으로 쓴다.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

# facts 에서 수치로 간주할 키들(financial_lookup + compute_change 커버)
_VALUE_KEYS = ("value", "value_from", "value_to", "delta")


def collect_fact_values(facts: Sequence[Mapping]) -> set[int]:
    """facts 의 모든 정수 수치를 모은다(검증 시 대조할 허용 값 집합)."""
    values: set[int] = set()
    for fact in facts:
        if fact.get("found") is False:
            continue
        for key in _VALUE_KEYS:
            v = fact.get(key)
            if isinstance(v, int):
                values.add(v)
    return values


def has_source(text: str) -> bool:
    """답변 산문에 출처 인용 표지가 있으면 True."""
    if not text:
        return False
    markers = ("출처", "보고서", "OpenDART", "공시")
    return any(m in text for m in markers)


def facts_have_source(facts: Sequence[Mapping]) -> bool:
    """조회된 facts 가 비어있지 않은 source 를 하나라도 가지면 True.

    structured output 에선 출처가 산문이 아니라 figures/facts 의 source 필드에 들어간다.
    따라서 숫자 답변의 출처는 산문 파싱이 아니라 이 구조화 값으로 판정한다(결정론).
    """
    return any(
        bool(f.get("source")) for f in facts if f.get("found") is not False
    )


def verify(
    figures: Sequence[Mapping],
    facts: Sequence[Mapping],
    draft: str,
) -> tuple[bool, str]:
    """(통과여부, 실패사유). 실패사유는 재시도 피드백으로 agent 에 되돌린다.

    규칙:
    1. figures 가 수치를 주장하는데 facts 가 비어 있으면 실패(환각 의심).
    2. figures 의 각 value 가 facts 의 허용 값 집합에 없으면 실패(근거 불일치).
    3. 수치를 주장하면(figures 비어있지 않음) 출처가 있어야 한다 —
       조회된 facts 의 source(구조화) 또는 산문 출처 표지 중 하나면 통과.
    4. figures 가 비어 있는 순수 서술 답변은 산문 출처 표지를 검사.
    """
    allowed = collect_fact_values(facts)

    if figures:
        if not allowed:
            return False, (
                "수치를 주장했으나 조회된 재무 값(facts)이 없습니다. 도구로 조회한 값만 인용하세요."
            )
        for fig in figures:
            claimed = fig.get("value")
            if not isinstance(claimed, int) or claimed not in allowed:
                return (
                    False,
                    f"주장한 수치 {claimed!r} 가 조회값과 일치하지 않습니다. "
                    "financial_lookup/compute_change 결과의 값만 사용하세요.",
                )
        # 출처: 구조화된 facts.source(우선) 또는 산문 표지 중 하나면 충족.
        if not (facts_have_source(facts) or has_source(draft)):
            return False, "수치 답변에 출처(보고서·연도)가 없습니다. 출처를 표기하세요."
        return True, ""

    # 순수 서술 답변
    if not has_source(draft):
        return False, "답변에 출처 표지가 없습니다. 공시 출처를 1개 이상 인용하세요."
    return True, ""
