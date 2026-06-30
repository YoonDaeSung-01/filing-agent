"""/ask 엔드포인트 — 네트워크/키 없이 모킹으로 템플릿·실패 처리를 검증.

실제 DART 호출은 키가 있을 때 수동으로 확인한다(자동 테스트는 모킹만 사용).
"""

import json
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from filing_agent.api import main
from filing_agent.api.main import app

FIXTURES = Path(__file__).parent / "fixtures"
client = TestClient(app)


def _fake_settings() -> SimpleNamespace:
    return SimpleNamespace(dart_api_key="dummy-key", dart_report_code="11011", dart_fs_div="CFS")


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_ask_returns_templated_revenue_answer(monkeypatch) -> None:
    monkeypatch.setattr(main, "get_settings", _fake_settings)
    monkeypatch.setattr(main.dart_client, "resolve_corp_code", lambda api_key, name: "00126380")
    monkeypatch.setattr(
        main.dart_client,
        "fetch_single_account",
        lambda api_key, *, corp_code, bsns_year, reprt_code: _load("fnlttSinglAcnt_cfs_ok.json"),
    )

    resp = client.get("/ask", params={"company": "삼성전자", "year": 2024})

    assert resp.status_code == 200
    body = resp.json()
    assert body["fact"]["value"] == 300_870_903_000_000
    assert body["fact"]["fs_div"] == "CFS"
    assert "삼성전자가 공시한 2024년 매출액은 약 300,870,903,000,000원입니다." in body["answer"]
    assert "출처:" in body["answer"]


def test_ask_unknown_company_returns_200_with_message(monkeypatch) -> None:
    # 데이터를 못 찾아도 500 이 아니라 200 + 안내 메시지
    monkeypatch.setattr(main, "get_settings", _fake_settings)
    monkeypatch.setattr(main.dart_client, "resolve_corp_code", lambda api_key, name: None)

    resp = client.get("/ask", params={"company": "없는회사명", "year": 2024})

    assert resp.status_code == 200
    body = resp.json()
    assert body["fact"] is None
    assert "corp_code" in body["answer"]


# ── POST /ask (에이전트) — 그래프를 모킹해 응답 스키마(facts 노출)만 검증 ──────────

class _FakeGraph:
    """graph.invoke 를 흉내내어 고정 final state 를 반환."""

    def __init__(self, final: dict) -> None:
        self._final = final

    def invoke(self, initial, config=None):  # noqa: ANN001
        return self._final


def _patch_graph(monkeypatch, final: dict) -> None:
    # ask_agent 가 함수 내부에서 import 하므로 graph 모듈의 get_graph 를 패치.
    from filing_agent.agent import graph as graph_mod

    monkeypatch.setattr(graph_mod, "get_graph", lambda: _FakeGraph(final))


def test_post_ask_surfaces_facts_for_cards(monkeypatch) -> None:
    """프론트 카드 렌더의 전제 — facts 가 응답에 그대로 노출되는지."""
    fact = {
        "company": "삼성전자", "account": "매출액", "year": 2024,
        "value": 300_870_903_000_000, "fs_div": "CFS", "source": "삼성전자 2024 사업보고서",
    }
    _patch_graph(monkeypatch, {
        "answer": "삼성전자가 공시한 2024년 매출액은 300조 8,709억원입니다. (출처: ...)",
        "sources": ["삼성전자 2024 사업보고서"],
        "tool_log": [{"tool": "financial_lookup", "args": {"company": "삼성전자"}, "ok": True}],
        "facts": [fact],
    })

    resp = client.post("/ask", json={"question": "삼성전자 2024년 매출액은?"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["facts"] == [fact]           # 카드 렌더용 구조화 값이 그대로 노출
    assert body["facts"][0]["value"] == 300_870_903_000_000
    assert body["tool_log"][0]["tool"] == "financial_lookup"
    assert body["sources"] == ["삼성전자 2024 사업보고서"]
    assert body["status"] == "ok"            # 정상 경로


def test_post_ask_facts_defaults_to_empty_list(monkeypatch) -> None:
    """순수 서술(doc_search)·가드레일 차단 등 facts 가 없을 때 빈 리스트로 안전하게 노출."""
    _patch_graph(monkeypatch, {
        "answer": "매수·매도 추천은 제공하지 않습니다.",
        "sources": [],
        "tool_log": [],
        "status": "blocked",
        # facts 키 자체가 없음 → 응답에서 [] 로 폴백돼야 함
    })

    resp = client.post("/ask", json={"question": "삼성전자 주식 사야 할까?"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["facts"] == []
    assert body["tool_log"] == []
    assert body["status"] == "blocked"       # 가드레일 차단 → 프론트가 결정론적으로 분기
