"""한투 KIS 시세 조회 — 국내주식 현재가(REST). vps 전용.

시세는 **사실 데이터**만 반환한다. 투자 조언·해석 없음.
PER/PBR 등 해석 여지가 큰 지표는 (사용자 결정: 사실만·해석 없음) 노출하지 않는다.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from filing_agent.config import Settings, get_settings
from filing_agent.platform.market.kis_client import KisApiError, get_access_token

logger = logging.getLogger(__name__)

_TIMEOUT_SEC = 10.0
_PRICE_PATH = "/uapi/domestic-stock/v1/quotations/inquire-price"
_TR_CURRENT_PRICE = "FHKST01010100"  # 국내주식 현재가 시세


def _to_int(v: Any) -> int:
    try:
        return int(str(v).replace(",", "").strip() or 0)
    except (ValueError, TypeError):
        return 0


def _to_float(v: Any) -> float:
    try:
        return float(str(v).replace(",", "").strip() or 0)
    except (ValueError, TypeError):
        return 0.0


def get_current_price(ticker: str, settings: Settings | None = None) -> dict[str, Any]:
    """국내주식 현재가·당일 시세를 반환한다(사실만). vps.

    ticker: 6자리 종목코드.
    반환: {ticker, price, change(부호포함), change_pct, open, high, low, volume,
           market_cap_eok(시가총액·억원), w52_high, w52_low}
    """
    cfg = settings or get_settings()
    token = get_access_token(cfg)  # 캐시 우선(1분당 1회 제한 대응)
    headers = {
        "content-type": "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "appkey": cfg.kis_app_key,
        "appsecret": cfg.kis_app_secret,
        "tr_id": _TR_CURRENT_PRICE,
    }
    params = {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": ticker}
    resp = httpx.get(
        f"{cfg.kis_base_url}{_PRICE_PATH}",
        headers=headers,
        params=params,
        timeout=_TIMEOUT_SEC,
    )
    resp.raise_for_status()
    payload: dict[str, Any] = resp.json()

    if payload.get("rt_cd") != "0":
        raise KisApiError(f"현재가 조회 실패(msg_cd={payload.get('msg_cd')}).")

    out = payload.get("output", {})
    return {
        "ticker": ticker,
        "price": _to_int(out.get("stck_prpr")),
        "change": _to_int(out.get("prdy_vrss")),  # 이미 부호 포함
        "change_pct": _to_float(out.get("prdy_ctrt")),
        "open": _to_int(out.get("stck_oprc")),
        "high": _to_int(out.get("stck_hgpr")),
        "low": _to_int(out.get("stck_lwpr")),
        "volume": _to_int(out.get("acml_vol")),
        "market_cap_eok": _to_int(out.get("hts_avls")),  # 억원 단위
        "w52_high": _to_int(out.get("w52_hgpr")),
        "w52_low": _to_int(out.get("w52_lwpr")),
    }
