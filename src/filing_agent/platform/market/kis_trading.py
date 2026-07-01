"""한투 KIS 모의투자(vps) — 잔고 조회 + 현금 주문.

★모의투자(vps) 전용★. 실전 주문은 만들지 않는다(영구 제외).
비밀값은 Settings(.env)에서만. 하드코딩·로깅 금지.

주문 실행은 계좌주(사용자)가 UI에서 한다. 이 모듈은 위임 클라이언트일 뿐이다.
"""

from __future__ import annotations

import logging
from typing import Any, Literal

import httpx

from filing_agent.config import Settings, get_settings
from filing_agent.platform.market.kis_client import KisApiError, get_access_token

logger = logging.getLogger(__name__)

_TIMEOUT_SEC = 10.0
_ACNT_PRDT_CD = "01"  # 위탁계좌 상품코드

# 모의투자(vps) tr_id
_TR_BALANCE = "VTTC8434R"  # 주식잔고조회
_TR_BUY = "VTTC0802U"  # 현금 매수
_TR_SELL = "VTTC0801U"  # 현금 매도

_BALANCE_PATH = "/uapi/domestic-stock/v1/trading/inquire-balance"
_ORDER_PATH = "/uapi/domestic-stock/v1/trading/order-cash"

Side = Literal["buy", "sell"]


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


def _headers(cfg: Settings, tr_id: str) -> dict[str, str]:
    return {
        "content-type": "application/json; charset=utf-8",
        "authorization": f"Bearer {get_access_token(cfg)}",
        "appkey": cfg.kis_app_key,
        "appsecret": cfg.kis_app_secret,
        "tr_id": tr_id,
        "custtype": "P",  # 개인
    }


def get_balance(settings: Settings | None = None) -> dict[str, Any]:
    """모의투자 잔고·보유종목·평가손익을 반환한다(사실만).

    반환: {cash(예수금), eval_amount(총평가금액), pnl(총평가손익),
           pnl_rate(%), positions:[{ticker,name,qty,avg_price,price,eval_amount,pnl,pnl_rate}]}
    """
    cfg = settings or get_settings()
    if not cfg.kis_account_no:
        raise KisApiError("KIS_ACCOUNT_NO 가 설정되지 않았습니다(.env).")

    params = {
        "CANO": cfg.kis_account_no,
        "ACNT_PRDT_CD": _ACNT_PRDT_CD,
        "AFHR_FLPR_YN": "N",
        "OFL_YN": "",
        "INQR_DVSN": "02",
        "UNPR_DVSN": "01",
        "FUND_STTL_ICLD_YN": "N",
        "FNCG_AMT_AUTO_RDPT_YN": "N",
        "PRCS_DVSN": "00",
        "CTX_AREA_FK100": "",
        "CTX_AREA_NK100": "",
    }
    resp = httpx.get(
        f"{cfg.kis_base_url}{_BALANCE_PATH}",
        headers=_headers(cfg, _TR_BALANCE),
        params=params,
        timeout=_TIMEOUT_SEC,
    )
    resp.raise_for_status()
    payload: dict[str, Any] = resp.json()
    if payload.get("rt_cd") != "0":
        raise KisApiError(f"잔고 조회 실패(msg_cd={payload.get('msg_cd')}).")

    summary = (payload.get("output2") or [{}])[0]
    cash = _to_int(summary.get("dnca_tot_amt"))
    eval_amount = _to_int(summary.get("tot_evlu_amt"))
    pnl = _to_int(summary.get("evlu_pfls_smtl_amt"))
    # 총수익률: 평가손익 / (평가금액 - 평가손익) — 원금 대비
    principal = eval_amount - pnl
    pnl_rate = round(pnl / principal * 100, 2) if principal else 0.0

    positions = []
    for row in payload.get("output1") or []:
        qty = _to_int(row.get("hldg_qty"))
        if qty <= 0:
            continue
        positions.append(
            {
                "ticker": row.get("pdno"),
                "name": row.get("prdt_name"),
                "qty": qty,
                "avg_price": _to_int(row.get("pchs_avg_pric")),
                "price": _to_int(row.get("prpr")),
                "eval_amount": _to_int(row.get("evlu_amt")),
                "pnl": _to_int(row.get("evlu_pfls_amt")),
                "pnl_rate": _to_float(row.get("evlu_pfls_rt")),
            }
        )

    return {
        "cash": cash,
        "eval_amount": eval_amount,
        "pnl": pnl,
        "pnl_rate": pnl_rate,
        "positions": positions,
    }


def place_order(
    ticker: str,
    side: Side,
    qty: int,
    *,
    order_type: str = "01",
    price: int = 0,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """모의투자 현금 주문(매수/매도)을 위임한다. vps.

    order_type: "01"=시장가(가격 무시), "00"=지정가(price 사용).
    반환: {ok, order_no, message}
    ※ 실행 주체는 계좌주(사용자)다. 시장가 시 price=0.
    """
    cfg = settings or get_settings()
    if not cfg.kis_account_no:
        raise KisApiError("KIS_ACCOUNT_NO 가 설정되지 않았습니다(.env).")

    tr_id = _TR_BUY if side == "buy" else _TR_SELL
    body = {
        "CANO": cfg.kis_account_no,
        "ACNT_PRDT_CD": _ACNT_PRDT_CD,
        "PDNO": ticker,
        "ORD_DVSN": order_type,
        "ORD_QTY": str(qty),
        "ORD_UNPR": str(price if order_type == "00" else 0),
    }
    resp = httpx.post(
        f"{cfg.kis_base_url}{_ORDER_PATH}",
        headers=_headers(cfg, tr_id),
        json=body,
        timeout=_TIMEOUT_SEC,
    )
    resp.raise_for_status()
    payload: dict[str, Any] = resp.json()
    if payload.get("rt_cd") != "0":
        return {"ok": False, "order_no": None, "message": payload.get("msg1", "주문 실패")}

    out = payload.get("output", {})
    return {"ok": True, "order_no": out.get("ODNO"), "message": payload.get("msg1", "주문 완료")}
