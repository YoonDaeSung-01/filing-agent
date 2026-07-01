"""상장사 검색 — startswith 우선순위·부분일치 검증(맵 모킹)."""

from types import SimpleNamespace

from fastapi.testclient import TestClient

from filing_agent.api import main
from filing_agent.api.main import app
from filing_agent.ingest import dart_client

client = TestClient(app)

_MAP = {
    "삼성전자": "005930",
    "삼성전기": "009150",
    "삼성SDI": "006400",
    "DB하이텍": "000990",
    "에스디바이오센서": "137310",  # '삼성' 미포함 — 검색 제외 대상
}


def test_search_prioritizes_startswith(monkeypatch):
    monkeypatch.setattr(dart_client, "_load_stock_code_map", lambda api_key: dict(_MAP))
    res = dart_client.search_listed_companies("dummy", "삼성", limit=10)
    names = [r["name"] for r in res]
    assert names[0] == "삼성전자"  # 최단 startswith 우선
    assert "에스디바이오센서" not in names
    assert all(r["ticker"] for r in res)


def test_search_empty_query_returns_empty(monkeypatch):
    monkeypatch.setattr(dart_client, "_load_stock_code_map", lambda api_key: dict(_MAP))
    assert dart_client.search_listed_companies("dummy", "  ", limit=10) == []


def test_search_endpoint(monkeypatch):
    monkeypatch.setattr(main, "get_settings", lambda: SimpleNamespace(dart_api_key="d"))
    monkeypatch.setattr(dart_client, "_load_stock_code_map", lambda api_key: dict(_MAP))
    r = client.get("/stock/search", params={"q": "삼성", "limit": 3})
    assert r.status_code == 200
    results = r.json()["results"]
    assert len(results) == 3
    assert results[0]["name"] == "삼성전자"
