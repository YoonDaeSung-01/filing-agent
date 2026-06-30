"""LangGraph ReAct 에이전트 그래프 + 하네스(Phase 4).

토폴로지:
    START → input_guard ─(block)─► END
              │(pass)
           call_model ─(tool_calls)─► call_tools ─(steps<MAX)─► call_model
              │(없음)                    │(steps>=MAX)
           finalize                   graceful_fail ─► END
              │
            verify ─(ok)─► output_guard ─► END
              ├─(retry)─► call_model
              └─(giveup)─► graceful_fail ─► END

테스트에서는 _build_llm / _build_finalizer 를 패치해 가짜 LLM 을 주입한다.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, StateGraph

from filing_agent.agent.state import AgentState, AnswerSchema
from filing_agent.agent.tools import TOOLS
from filing_agent.config import get_settings
from filing_agent.harness import guardrails
from filing_agent.harness.verifier import verify as verify_answer

logger = logging.getLogger(__name__)

# 수치 도구(성공 시 facts 에 적재)
_FACT_TOOLS = {"financial_lookup", "compute_change", "compute_sum"}

_SYSTEM_PROMPT = (
    "당신은 DART 전자공시 기반 재무 사실 추출 어시스턴트입니다.\n"
    "규칙:\n"
    "① 제공된 공시 자료 내에서만 답하고, 출처(회사·연도·보고서)를 항상 표기하세요.\n"
    "② 재무 수치는 반드시 financial_lookup 또는 compute_change 도구를 사용하세요. "
    "직접 계산하거나 기억에서 숫자를 가져오지 마세요.\n"
    "②-1 여러 회사의 수치를 합산할 때(예: 'A사와 B사의 매출 합계')는 compute_sum 에 "
    "회사 목록을 한 번에 넘기세요. 직접 더하지 마세요.\n"
    "③ 서술·전략·위험 등 비정형 질문은 doc_search를 사용하세요.\n"
    "④ 자료에 없으면 '확인할 수 없습니다'라고 답하세요.\n"
    "⑤ 투자 매수·매도 조언은 하지 않습니다.\n"
    "⑥ 질문에 회사명·연도가 불명확하면 숫자를 추측하지 말고, "
    "어떤 회사·연도를 묻는지 사용자에게 되물으세요."
)


# ── LLM 팩토리(테스트에서 패치) ───────────────────────────────────────────────
def _build_llm() -> Any:
    """ReAct 루프용 — 도구 바인딩 LLM."""
    cfg = get_settings()
    from langchain_litellm import ChatLiteLLM
    return ChatLiteLLM(model=cfg.llm_model, api_key=cfg.llm_api_key).bind_tools(TOOLS)


def _build_finalizer() -> Any:
    """finalize용 — 구조화 출력 LLM(AnswerSchema)."""
    cfg = get_settings()
    from langchain_litellm import ChatLiteLLM
    return ChatLiteLLM(model=cfg.llm_model, api_key=cfg.llm_api_key).with_structured_output(
        AnswerSchema
    )


# ── 노드 ──────────────────────────────────────────────────────────────────────
def _node_input_guard(state: AgentState) -> dict:
    cfg = get_settings()
    result = guardrails.check_input(state["question"], max_chars=cfg.agent_max_question_chars)
    if result["action"] == "block":
        return {"status": "blocked", "answer": result["answer"], "sources": []}
    return {"status": None}


def _node_call_model(state: AgentState) -> dict:
    llm = _build_llm()
    messages = list(state["messages"])

    if not messages:
        question = state["question"]
        company = state.get("company")
        year = state.get("year")
        note = ""
        if company:
            note = f" (회사: {company}" + (f", 연도: {year}" if year else "") + ")"
        messages = [
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=question + note),
        ]
        response = llm.invoke(messages)
        # 초기 시스템/사용자 메시지도 함께 반환해 상태에 누적
        return {"messages": messages + [response]}

    # 재시도: 검증 피드백이 있으면 사용자 메시지로 추가
    feedback = state.get("verifier_feedback")
    if feedback:
        messages = messages + [HumanMessage(content=f"[검증 피드백] {feedback}")]
        response = llm.invoke(messages)
        return {"messages": [HumanMessage(content=f"[검증 피드백] {feedback}"), response],
                "verifier_feedback": None}

    response = llm.invoke(messages)
    return {"messages": [response]}


def _node_call_tools(state: AgentState) -> dict:
    last_msg: AIMessage = state["messages"][-1]
    tool_map = {t.name: t for t in TOOLS}

    tool_messages: list[ToolMessage] = []
    tool_log: list[dict] = list(state.get("tool_log") or [])
    new_facts: list[dict] = []
    new_doc_sources: list[str] = []
    steps = state.get("steps", 0)

    for tc in last_msg.tool_calls:
        name, args, call_id = tc["name"], tc["args"], tc["id"]
        fn = tool_map.get(name)
        if fn is None:
            result, ok = {"error": f"알 수 없는 도구: {name}"}, False
        else:
            try:
                result, ok = fn.invoke(args), True
            except Exception as exc:  # noqa: BLE001
                logger.warning("도구 %s 실패: %s", name, exc)
                result, ok = {"error": str(exc)}, False

        tool_log.append({"tool": name, "args": args, "ok": ok})
        # 수치 도구 성공 결과를 facts 에 구조화 적재(검증 근거)
        is_fact = (
            ok and name in _FACT_TOOLS
            and isinstance(result, dict) and result.get("found") is not False
        )
        if is_fact:
            new_facts.append(result)
        # doc_search 성공 결과의 출처를 누적(서술형 답변 출처 표기)
        if ok and name == "doc_search" and isinstance(result, list):
            new_doc_sources.extend(
                c["source"] for c in result
                if isinstance(c, dict) and c.get("source")
            )
        tool_messages.append(
            ToolMessage(content=json.dumps(result, ensure_ascii=False), tool_call_id=call_id)
        )

    out: dict = {
        "messages": tool_messages,
        "tool_log": tool_log,
        "steps": steps + len(last_msg.tool_calls),
    }
    if new_facts:
        out["facts"] = new_facts  # operator.add 리듀서로 누적
    if new_doc_sources:
        out["doc_sources"] = new_doc_sources  # operator.add 리듀서로 누적
    return out


def _node_finalize(state: AgentState) -> dict:
    """구조화 출력으로 {answer, figures} 생성. 스키마 파싱 실패 시 폴백(크래시 방지)."""
    try:
        finalizer = _build_finalizer()
        result = finalizer.invoke(list(state["messages"]))
        answer = result.get("answer", "") if isinstance(result, dict) else ""
        figures = result.get("figures", []) if isinstance(result, dict) else []
        return {"draft": answer, "figures": list(figures)}
    except Exception as exc:  # noqa: BLE001
        # 스키마 파싱 실패 → 마지막 응답 텍스트로 폴백(figures 비움 → verify 가 처리)
        logger.warning("finalize 구조화 출력 실패(%s) — 폴백 사용", type(exc).__name__)
        last = state["messages"][-1] if state["messages"] else None
        fallback = getattr(last, "content", "") or "답변을 생성하지 못했습니다."
        return {"draft": fallback, "figures": []}


def _node_verify(state: AgentState) -> dict:
    cfg = get_settings()
    figures = state.get("figures") or []
    facts = state.get("facts") or []
    draft = state.get("draft") or ""

    ok, reason = verify_answer(figures, facts, draft)
    if ok:
        return {"status": "ok"}

    attempts = state.get("verify_attempts", 0) + 1
    if attempts >= cfg.agent_max_verify_attempts:
        return {"status": "giveup", "verify_attempts": attempts, "verifier_feedback": reason}
    return {"status": "retry", "verify_attempts": attempts, "verifier_feedback": reason}


def _node_output_guard(state: AgentState) -> dict:
    draft = state.get("draft") or ""
    figures = state.get("figures") or []
    sources = _collect_sources(state)
    result = guardrails.check_output(
        draft, has_figures=bool(figures), has_sources=bool(sources)
    )
    return {"answer": result["answer"], "sources": sources}


def _node_graceful_fail(state: AgentState) -> dict:
    facts = state.get("facts") or []
    confirmed = _summarize_facts(facts)
    reason = state.get("verifier_feedback") or "검증/스텝 예산 도달"
    answer = (
        "확정된 답을 찾지 못했습니다. "
        f"확인된 부분: {confirmed}. (사유: {reason}) "
        "질문을 회사·연도·계정으로 좁혀 주시면 다시 시도합니다."
    )
    # status="failed" 로 최종 상태를 자기 기술적으로 만든다(blocked/ok 와 구분).
    return {"answer": answer, "sources": _collect_sources(state), "status": "failed"}


# ── 라우팅 ────────────────────────────────────────────────────────────────────
def _route_after_input_guard(state: AgentState) -> str:
    return "blocked" if state.get("status") == "blocked" else "call_model"


def _route_after_model(state: AgentState) -> str:
    last = state["messages"][-1]
    if getattr(last, "tool_calls", None):
        return "call_tools"
    return "finalize"


def _route_after_tools(state: AgentState) -> str:
    cfg = get_settings()
    if state.get("steps", 0) >= cfg.agent_max_steps:
        return "graceful_fail"
    return "call_model"


def _route_after_verify(state: AgentState) -> str:
    return {"ok": "output_guard", "retry": "call_model", "giveup": "graceful_fail"}[
        state["status"]
    ]


# ── 헬퍼 ──────────────────────────────────────────────────────────────────────
def _sources_from_facts(facts: list[dict]) -> list[str]:
    srcs: list[str] = []
    for f in facts:
        if f.get("found") is False:
            continue
        src = f.get("source")
        if isinstance(src, list):  # compute_sum 은 회사별 출처 리스트
            srcs.extend(src)
        elif src:
            srcs.append(src)
    return list(dict.fromkeys(filter(None, srcs)))


def _collect_sources(state: AgentState) -> list[str]:
    """수치(facts) 출처 + 서술(doc_search) 출처를 합쳐 중복 제거(등장 순서 유지)."""
    srcs = _sources_from_facts(state.get("facts") or [])
    srcs += list(state.get("doc_sources") or [])
    return list(dict.fromkeys(filter(None, srcs)))


def _summarize_facts(facts: list[dict]) -> str:
    if not facts:
        return "없음"
    parts = []
    for f in facts:
        if f.get("found") is False:
            continue
        acc = f.get("account", "?")
        if "total" in f:  # compute_sum
            companies = "+".join(f.get("companies") or [])
            parts.append(f"{companies} {f.get('year')}년 {acc} 합계 {f['total']:,}원")
        elif "value" in f:
            parts.append(f"{acc} {f.get('year')}년 {f['value']:,}원")
        elif "delta" in f:
            parts.append(f"{acc} {f.get('year_from')}→{f.get('year_to')} 증감 {f['delta']:,}원")
    return "; ".join(parts) if parts else "없음"


# ── 그래프 빌드 ────────────────────────────────────────────────────────────────
def build_graph() -> Any:
    builder = StateGraph(AgentState)

    builder.add_node("input_guard", _node_input_guard)
    builder.add_node("call_model", _node_call_model)
    builder.add_node("call_tools", _node_call_tools)
    builder.add_node("finalize", _node_finalize)
    builder.add_node("verify", _node_verify)
    builder.add_node("output_guard", _node_output_guard)
    builder.add_node("graceful_fail", _node_graceful_fail)

    builder.add_edge(START, "input_guard")
    builder.add_conditional_edges(
        "input_guard", _route_after_input_guard,
        {"blocked": END, "call_model": "call_model"},
    )
    builder.add_conditional_edges(
        "call_model", _route_after_model,
        {"call_tools": "call_tools", "finalize": "finalize"},
    )
    builder.add_conditional_edges(
        "call_tools", _route_after_tools,
        {"call_model": "call_model", "graceful_fail": "graceful_fail"},
    )
    builder.add_edge("finalize", "verify")
    builder.add_conditional_edges(
        "verify", _route_after_verify,
        {
            "output_guard": "output_guard",
            "call_model": "call_model",
            "graceful_fail": "graceful_fail",
        },
    )
    builder.add_edge("output_guard", END)
    builder.add_edge("graceful_fail", END)

    return builder.compile()


_agent_graph = None


def get_graph() -> Any:
    global _agent_graph
    if _agent_graph is None:
        _agent_graph = build_graph()
    return _agent_graph
