"""LangGraph ReAct 에이전트 그래프.

토폴로지:
    START → call_model → (should_continue) → call_tools → call_model → ...
                                           ↘ END
"""

from __future__ import annotations

import json
from typing import Any, Literal

from langchain_core.messages import AIMessage, ToolMessage
from langchain_litellm import ChatLiteLLM
from langgraph.graph import END, START, StateGraph

from filing_agent.agent.state import AgentState
from filing_agent.agent.tools import TOOLS
from filing_agent.config import get_settings


def _build_llm() -> Any:
    cfg = get_settings()
    llm = ChatLiteLLM(model=cfg.llm_model, api_key=cfg.llm_api_key)
    return llm.bind_tools(TOOLS)


_SYSTEM_PROMPT = (
    "당신은 DART 전자공시 기반 재무 사실 추출 어시스턴트입니다.\n"
    "규칙:\n"
    "① 제공된 공시 자료 내에서만 답하고, 출처(회사·연도·보고서)를 항상 표기하세요.\n"
    "② 재무 수치는 반드시 financial_lookup 또는 compute_change 도구를 사용하세요. "
    "직접 계산하거나 기억에서 숫자를 가져오지 마세요.\n"
    "③ 서술·전략·위험 등 비정형 질문은 doc_search를 사용하세요.\n"
    "④ 자료에 없으면 '확인할 수 없습니다'라고 답하세요.\n"
    "⑤ 투자 매수·매도 조언은 하지 않습니다."
)


def _node_call_model(state: AgentState) -> dict:
    """LLM 호출 — 도구 요청 또는 최종 답변을 결정한다."""
    from langchain_core.messages import HumanMessage, SystemMessage

    llm = _build_llm()
    messages = state["messages"]

    # 첫 호출이면 시스템 + 사용자 메시지 구성
    if not messages:
        question = state["question"]
        company = state.get("company")
        year = state.get("year")
        context_note = ""
        if company:
            context_note += f" (회사: {company}"
            if year:
                context_note += f", 연도: {year}"
            context_note += ")"
        messages = [
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=question + context_note),
        ]

    response: AIMessage = llm.invoke(messages)
    return {"messages": [response]}


def _node_call_tools(state: AgentState) -> dict:
    """도구 실행 — 마지막 AIMessage의 tool_calls를 실행하고 ToolMessage로 반환."""
    last_msg: AIMessage = state["messages"][-1]
    tool_map = {t.name: t for t in TOOLS}

    tool_messages: list[ToolMessage] = []
    tool_log: list[dict] = list(state.get("tool_log") or [])
    steps = state.get("steps", 0)

    for tc in last_msg.tool_calls:
        tool_name = tc["name"]
        args = tc["args"]
        tool_call_id = tc["id"]

        fn = tool_map.get(tool_name)
        if fn is None:
            result = {"error": f"알 수 없는 도구: {tool_name}"}
            ok = False
        else:
            try:
                result = fn.invoke(args)
                ok = True
            except Exception as exc:
                result = {"error": str(exc)}
                ok = False

        tool_log.append({"tool": tool_name, "args": args, "ok": ok})
        tool_messages.append(
            ToolMessage(
                content=json.dumps(result, ensure_ascii=False),
                tool_call_id=tool_call_id,
            )
        )

    return {
        "messages": tool_messages,
        "tool_log": tool_log,
        "steps": steps + len(last_msg.tool_calls),
    }


def _should_continue(state: AgentState) -> Literal["call_tools", "__end__"]:
    """마지막 메시지에 tool_calls 가 있고 예산이 남으면 도구 실행, 아니면 종료."""
    cfg = get_settings()
    last_msg = state["messages"][-1]
    tool_calls = getattr(last_msg, "tool_calls", None)
    if tool_calls and state.get("steps", 0) < cfg.agent_max_steps:
        return "call_tools"
    return "__end__"


def _extract_final(state: AgentState) -> dict:
    """그래프 종료 시 answer·sources 추출."""
    last_msg = state["messages"][-1]
    answer: str = ""
    if isinstance(last_msg, AIMessage):
        answer = last_msg.content or ""
    # steps 초과로 종료된 경우 최소 안내
    if not answer:
        tool_log = state.get("tool_log") or []
        done = [lg["tool"] for lg in tool_log if lg.get("ok")]
        answer = (
            "최대 도구 호출 횟수에 도달해 완전한 답변을 생성하지 못했습니다. "
            f"확인된 부분: {done}. 질문을 회사·연도·계정으로 좁혀 다시 시도해주세요."
        )

    tool_log = state.get("tool_log") or []
    sources = [lg["args"].get("company", "") for lg in tool_log if lg.get("ok")]
    sources = list(dict.fromkeys(filter(None, sources)))  # 중복 제거

    return {"answer": answer, "sources": sources}


def build_graph() -> Any:
    """컴파일된 LangGraph 그래프를 반환한다."""
    builder = StateGraph(AgentState)

    builder.add_node("call_model", _node_call_model)
    builder.add_node("call_tools", _node_call_tools)
    builder.add_node("extract_final", _extract_final)

    builder.add_edge(START, "call_model")
    builder.add_conditional_edges(
        "call_model",
        _should_continue,
        {"call_tools": "call_tools", "__end__": "extract_final"},
    )
    builder.add_edge("call_tools", "call_model")
    builder.add_edge("extract_final", END)

    return builder.compile()


# 모듈 임포트 시 컴파일하지 않음 — 명시적 호출 시에만 생성
agent_graph = None


def get_graph() -> Any:
    global agent_graph
    if agent_graph is None:
        agent_graph = build_graph()
    return agent_graph
