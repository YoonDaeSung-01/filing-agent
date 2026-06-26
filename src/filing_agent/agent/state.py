"""LangGraph 에이전트 상태 스키마."""

from __future__ import annotations

from typing import Annotated

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class AgentState(TypedDict):
    question: str
    company: str | None
    year: int | None
    messages: Annotated[list[AnyMessage], add_messages]
    tool_log: list[dict]   # [{tool, args, ok}] — 관측/디버그용
    steps: int             # 누적 도구 호출 수 (예산 카운터)
    answer: str | None
    sources: list[str]
