"""한투 모의투자 잔고·주문 — 파싱·위임 검증(네트워크·토큰 모킹)."""

import pytest

from filing_agent.config import Settings
from filing_agent.platform.market import kis_trading
from filing_agent.platform.market.kis_client import KisApiError


class _FakeResp:
    def __init__(self, data: dict, status: int = 200):
        self._data = data
        self.status_code = status

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"http {self.status_code}")

    def json(self) -> dict:
        return self._data


def _cfg(**over) -> Settings:
    base = dict(dart_api_key="x", kis_app_key="k", kis_app_secret="s", kis_account_no="50195662")
    base.update(over)
    return Settings(**base)


# 라이브 확인분: 예수금 1천만·보유 0
_BALANCE = {
    "rt_cd": "0",
    "output1": [],
    "output2": [
        {"dnca_tot_amt": "10000000", "tot_evlu_amt": "10000000", "evlu_pfls_smtl_amt": "0"}
    ],
}

_BALANCE_WITH_POS = {
    "rt_cd": "0",
    "output1": [
        {
            "pdno": "005930",
            "prdt_name": "삼성전자",
            "hldg_qty": "10",
            "pchs_avg_pric": "320000",
            "prpr": "322000",
            "evlu_amt": "3220000",
            "evlu_pfls_amt": "20000",
            "evlu_pfls_rt": "0.62",
        }
    ],
    "output2": [
        {"dnca_tot_amt": "6800000", "tot_evlu_amt": "10020000", "evlu_pfls_smtl_amt": "20000"}
    ],
}


def test_balance_parses_empty(monkeypatch):
    monkeypatch.setattr(kis_trading, "get_access_token", lambda cfg=None: "T")
    monkeypatch.setattr(kis_trading.httpx, "get", lambda *a, **k: _FakeResp(_BALANCE))

    r = kis_trading.get_balance(_cfg())
    assert r["cash"] == 10_000_000
    assert r["eval_amount"] == 10_000_000
    assert r["pnl"] == 0
    assert r["positions"] == []


def test_balance_parses_positions_and_rate(monkeypatch):
    monkeypatch.setattr(kis_trading, "get_access_token", lambda cfg=None: "T")
    monkeypatch.setattr(kis_trading.httpx, "get", lambda *a, **k: _FakeResp(_BALANCE_WITH_POS))

    r = kis_trading.get_balance(_cfg())
    assert len(r["positions"]) == 1
    p = r["positions"][0]
    assert p["ticker"] == "005930"
    assert p["qty"] == 10
    assert p["pnl"] == 20000
    # 원금 = 평가금액 - 손익 = 10,000,000 → 수익률 0.2%
    assert r["pnl_rate"] == 0.2


def test_balance_no_account_raises(monkeypatch):
    with pytest.raises(KisApiError):
        kis_trading.get_balance(_cfg(kis_account_no=""))


def test_place_order_buy_success(monkeypatch):
    captured = {}

    def fake_post(url, headers, json, timeout):
        captured["tr_id"] = headers["tr_id"]
        captured["body"] = json
        return _FakeResp({"rt_cd": "0", "msg1": "주문 완료", "output": {"ODNO": "0001234"}})

    monkeypatch.setattr(kis_trading, "get_access_token", lambda cfg=None: "T")
    monkeypatch.setattr(kis_trading.httpx, "post", fake_post)

    r = kis_trading.place_order("005930", "buy", 10, settings=_cfg())
    assert r["ok"] is True
    assert r["order_no"] == "0001234"
    assert captured["tr_id"] == "VTTC0802U"  # 매수
    assert captured["body"]["ORD_QTY"] == "10"


def test_place_order_sell_uses_sell_tr(monkeypatch):
    captured = {}

    def fake_post(url, headers, json, timeout):
        captured["tr_id"] = headers["tr_id"]
        return _FakeResp({"rt_cd": "0", "output": {"ODNO": "9"}})

    monkeypatch.setattr(kis_trading, "get_access_token", lambda cfg=None: "T")
    monkeypatch.setattr(kis_trading.httpx, "post", fake_post)

    kis_trading.place_order("005930", "sell", 1, settings=_cfg())
    assert captured["tr_id"] == "VTTC0801U"  # 매도


def test_place_order_failure_returns_ok_false(monkeypatch):
    monkeypatch.setattr(kis_trading, "get_access_token", lambda cfg=None: "T")
    monkeypatch.setattr(
        kis_trading.httpx,
        "post",
        lambda *a, **k: _FakeResp({"rt_cd": "1", "msg1": "잔고 부족"}),
    )
    r = kis_trading.place_order("005930", "buy", 999999, settings=_cfg())
    assert r["ok"] is False
    assert "잔고" in r["message"]
