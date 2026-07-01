"""한투 KIS 시세 조회 — 국내주식 현재가(REST). vps 전용.

시세는 **사실 데이터**만 반환한다. 투자 조언·해석 없음.
PER/PBR 등 해석 여지가 큰 지표는 (사용자 결정: 사실만·해석 없음) 노출하지 않는다.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from filing_agent.config import Settings, get_settings
from filing_agent.platform.market.kis_client import KisApiError, get_access_token

logger = logging.getLogger(__name__)

_TIMEOUT_SEC = 10.0
_PRICE_PATH = "/uapi/domestic-stock/v1/quotations/inquire-price"
_TR_CURRENT_PRICE = "FHKST01010100"  # 국내주식 현재가 시세

_INTRADAY_PATH = "/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice"
_TR_INTRADAY = "FHKST03010200"  # 당일 분봉
_MKT_OPEN = "090000"
_MKT_CLOSE = "153000"


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


def get_intraday(ticker: str, settings: Settings | None = None, max_pages: int = 14) -> list[dict]:
    """당일 분봉을 시간 오름차순으로 반환한다(장중~마감). vps.

    한투는 1회 30건이라 마감(15:30)부터 개장(09:00)까지 역방향 페이지네이션한다.
    반환: [{date("HH:MM"), open, high, low, close, volume}, ...]
    """
    cfg = settings or get_settings()
    headers = {
        "content-type": "application/json; charset=utf-8",
        "authorization": f"Bearer {get_access_token(cfg)}",
        "appkey": cfg.kis_app_key,
        "appsecret": cfg.kis_app_secret,
        "tr_id": _TR_INTRADAY,
    }
    seen: dict[str, dict[str, Any]] = {}
    anchor = _MKT_CLOSE
    url = f"{cfg.kis_base_url}{_INTRADAY_PATH}"
    for i in range(max_pages):
        if i > 0:
            time.sleep(0.12)  # 레이트리밋 회피(초당 제한)
        params = {
            "FID_ETC_CLS_CODE": "",
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": ticker,
            "FID_INPUT_HOUR_1": anchor,
            "FID_PW_DATA_INCU_YN": "Y",
        }
        try:
            resp = httpx.get(url, headers=headers, params=params, timeout=_TIMEOUT_SEC)
            resp.raise_for_status()
            payload = resp.json()
        except httpx.HTTPError:
            break  # 페이지 실패 시 지금까지 모은 부분 데이터 반환
        if payload.get("rt_cd") != "0":
            break
        rows = payload.get("output2") or []
        if not rows:
            break
        for row in rows:
            t = (row.get("stck_cntg_hour") or "").strip()
            if t:
                seen.setdefault(t, row)
        oldest = (rows[-1].get("stck_cntg_hour") or "").strip()
        if not oldest or oldest <= _MKT_OPEN:
            break
        anchor = oldest

    items: list[dict] = []
    for t in sorted(seen):
        if t < _MKT_OPEN or t > _MKT_CLOSE:
            continue
        row = seen[t]
        items.append(
            {
                "date": f"{t[:2]}:{t[2:4]}",
                "open": _to_int(row.get("stck_oprc")),
                "high": _to_int(row.get("stck_hgpr")),
                "low": _to_int(row.get("stck_lwpr")),
                "close": _to_int(row.get("stck_prpr")),
                "volume": _to_int(row.get("cntg_vol")),
            }
        )
    return items
