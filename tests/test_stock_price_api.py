"""/stock/price 엔드포인트 — 종목명 해석 + 한투 시세를 모킹으로 검증(키·네트워크 없이)."""

from types import SimpleNamespace

from fastapi.testclient import TestClient

from filing_agent.api import main
from filing_agent.api.main import app
from filing_agent.platform.market import kis_market

client = TestClient(app)


def _fake_settings() -> SimpleNamespace:
    return SimpleNamespace(dart_api_key="dummy", dart_report_code="11011", dart_fs_div="CFS")


_PRICE = {
    "ticker": "005930",
    "price": 322000,
    "change": -12000,
    "change_pct": -3.59,
    "open": 334500,
    "high": 339000,
    "low": 319000,
    "volume": 8079781,
    "market_cap_eok": 18825017,
    "w52_high": 374500,
    "w52_low": 59800,
}


def test_stock_price_ok(monkeypatch):
    monkeypatch.setattr(main, "get_settings", _fake_settings)
    monkeypatch.setattr(main.dart_client, "resolve_stock_code", lambda api_key, name: "005930")
    monkeypatch.setattr(kis_market, "get_current_price", lambda ticker, settings=None: dict(_PRICE))

    resp = client.get("/stock/price", params={"company": "삼성전자"})
    assert resp.status_code == 200
    d = resp.json()
    assert d["found"] is True
    assert d["company"] == "삼성전자"
    assert d["ticker"] == "005930"
    assert d["price"] == 322000
    assert d["change"] == -12000


def test_stock_price_unknown_company(monkeypatch):
    monkeypatch.setattr(main, "get_settings", _fake_settings)
    monkeypatch.setattr(main.dart_client, "resolve_stock_code", lambda api_key, name: None)

    resp = client.get("/stock/price", params={"company": "없는회사"})
    assert resp.status_code == 200
    assert resp.json()["found"] is False


def test_stock_price_kis_error_returns_found_false(monkeypatch):
    """한투 호출 실패해도 500 아니라 200 + found:False."""
    monkeypatch.setattr(main, "get_settings", _fake_settings)
    monkeypatch.setattr(main.dart_client, "resolve_stock_code", lambda api_key, name: "005930")

    def _boom(ticker, settings=None):
        raise RuntimeError("KIS down")

    monkeypatch.setattr(kis_market, "get_current_price", _boom)

    resp = client.get("/stock/price", params={"company": "삼성전자"})
    assert resp.status_code == 200
    assert resp.json()["found"] is False
