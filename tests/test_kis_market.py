"""한투 현재가 조회 — 파싱·오류 처리 검증(네트워크·토큰 모킹)."""

import pytest

from filing_agent.config import Settings
from filing_agent.platform.market import kis_market
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
    base = dict(dart_api_key="x", kis_app_key="k", kis_app_secret="s", kis_account_no="5")
    base.update(over)
    return Settings(**base)


# 실제 한투 응답 필드(라이브 확인분)를 그대로 픽스처화
_OK = {
    "rt_cd": "0",
    "output": {
        "stck_prpr": "322000",
        "prdy_vrss": "-12000",
        "prdy_ctrt": "-3.59",
        "stck_oprc": "334500",
        "stck_hgpr": "339000",
        "stck_lwpr": "319000",
        "acml_vol": "8079781",
        "hts_avls": "18825017",
        "w52_hgpr": "374500",
        "w52_lwpr": "59800",
    },
}


def test_current_price_parses_real_shape(monkeypatch):
    monkeypatch.setattr(kis_market, "get_access_token", lambda cfg=None: "T")
    monkeypatch.setattr(kis_market.httpx, "get", lambda *a, **k: _FakeResp(_OK))

    r = kis_market.get_current_price("005930", _cfg())
    assert r["ticker"] == "005930"
    assert r["price"] == 322000
    assert r["change"] == -12000  # 부호 포함 그대로
    assert r["change_pct"] == -3.59
    assert r["high"] == 339000
    assert r["w52_low"] == 59800
    assert r["market_cap_eok"] == 18825017


def test_error_rt_cd_raises(monkeypatch):
    monkeypatch.setattr(kis_market, "get_access_token", lambda cfg=None: "T")
    monkeypatch.setattr(
        kis_market.httpx,
        "get",
        lambda *a, **k: _FakeResp({"rt_cd": "1", "msg_cd": "40580000", "msg1": "오류"}),
    )
    with pytest.raises(KisApiError):
        kis_market.get_current_price("005930", _cfg())


def test_int_parsing_handles_commas_and_blanks(monkeypatch):
    data = {"rt_cd": "0", "output": {"stck_prpr": "1,234", "prdy_vrss": "", "prdy_ctrt": "0.00"}}
    monkeypatch.setattr(kis_market, "get_access_token", lambda cfg=None: "T")
    monkeypatch.setattr(kis_market.httpx, "get", lambda *a, **k: _FakeResp(data))

    r = kis_market.get_current_price("005930", _cfg())
    assert r["price"] == 1234
    assert r["change"] == 0  # 빈 문자열 → 0
