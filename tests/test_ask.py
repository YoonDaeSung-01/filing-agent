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
