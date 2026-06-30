"""LangGraph 에이전트 상태 스키마 + 구조화 답변 스키마(Phase 4)."""

from __future__ import annotations

import operator
from typing import Annotated

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class Figure(TypedDict):
    """답변이 인용한 수치 — 검증 대상(finalize가 structured output으로 채운다)."""

    account: str
    year: int
    value: int  # 원 단위 정수 (LLM이 주장한 값)
    source: str


class AnswerSchema(TypedDict):
    """finalize 노드가 with_structured_output 으로 받는 답변 구조."""

    answer: str            # 사용자에게 보일 산문 답변
    figures: list[Figure]  # 답변이 인용한 수치(검증 대상)


class AgentState(TypedDict):
    question: str
    company: str | None
    year: int | None
    messages: Annotated[list[AnyMessage], add_messages]
    tool_log: list[dict]   # [{tool, args, ok}] — 관측/디버그용
    steps: int             # 누적 도구 호출 수 (예산 카운터)
    # ── Phase 4 ──
    facts: Annotated[list[dict], operator.add]  # 수치 도구 성공 결과 누적(검증 근거)
    doc_sources: Annotated[list[str], operator.add]  # doc_search 결과 출처 누적(서술형 출처)
    draft: str | None                            # finalize 산문 답변(AnswerSchema.answer)
    figures: list[dict]                          # finalize 주장 수치(검증 대상)
    verifier_feedback: str | None                # 검증 실패 피드백(재시도 시 agent에 전달)
    verify_attempts: int                         # 검증 재시도 카운터(별도 예산)
    status: str | None                           # "ok" | "retry" | "giveup" | "blocked"
    answer: str | None
    sources: list[str]
