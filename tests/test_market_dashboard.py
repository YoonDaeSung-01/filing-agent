"""GET /market/movers, /market/sectors — 모킹으로 검증(키·네트워크 없이)."""

from types import SimpleNamespace

from fastapi.testclient import TestClient

from filing_agent.api import main
from filing_agent.api.main import app
from filing_agent.platform.market import kis_market

client = TestClient(app)


def _fake_settings() -> SimpleNamespace:
    return SimpleNamespace(dart_api_key="dummy")


def test_market_movers_ok(monkeypatch):
    monkeypatch.setattr(main, "get_settings", _fake_settings)

    def fake_movers(direction, settings=None):
        return [
            {"name": "테스트", "ticker": "000001", "price": 1000, "change": 100, "change_pct": 10.0}
        ]

    monkeypatch.setattr(kis_market, "get_market_movers", fake_movers)

    resp = client.get("/market/movers")
    assert resp.status_code == 200
    body = resp.json()
    assert body["found"] is True
    assert len(body["gainers"]) == 1
    assert len(body["losers"]) == 1


def test_market_movers_error_returns_found_false(monkeypatch):
    monkeypatch.setattr(main, "get_settings", _fake_settings)

    def boom(direction, settings=None):
        raise RuntimeError("KIS down")

    monkeypatch.setattr(kis_market, "get_market_movers", boom)

    resp = client.get("/market/movers")
    assert resp.status_code == 200
    assert resp.json()["found"] is False


def test_market_sectors_ok(monkeypatch):
    monkeypatch.setattr(main, "get_settings", _fake_settings)
    monkeypatch.setattr(main.dart_client, "resolve_stock_code", lambda api_key, name: "005930")
    def fake_price(ticker, settings=None):
        return {"ticker": ticker, "price": 100, "change": 1, "change_pct": 1.0}

    monkeypatch.setattr(kis_market, "get_current_price", fake_price)
    monkeypatch.setattr(main, "time", SimpleNamespace(sleep=lambda s: None))

    resp = client.get("/market/sectors")
    assert resp.status_code == 200
    body = resp.json()
    assert body["found"] is True
    assert len(body["sectors"]) == 4  # SECTOR_MAP 카테고리 수
    for sector in body["sectors"]:
        assert len(sector["stocks"]) == len(sector["stocks"])  # 전부 resolve_stock_code 성공 가정


def test_market_sectors_unresolvable_company_skipped(monkeypatch):
    monkeypatch.setattr(main, "get_settings", _fake_settings)
    monkeypatch.setattr(main.dart_client, "resolve_stock_code", lambda api_key, name: None)
    monkeypatch.setattr(main, "time", SimpleNamespace(sleep=lambda s: None))

    resp = client.get("/market/sectors")
    assert resp.status_code == 200
    for sector in resp.json()["sectors"]:
        assert sector["stocks"] == []
