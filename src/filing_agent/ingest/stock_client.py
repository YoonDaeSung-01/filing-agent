"""주가 데이터 클라이언트 — FinanceDataReader 래퍼 + 디스크 캐싱(일일 1회).

규칙:
- API 키 불필요 (FinanceDataReader → KRX / Yahoo)
- 캐시: data/raw/stock/{ticker}_{YYYY-MM-DD}.json (날짜 단위)
- 반환 값은 타입 있는 사실 데이터. 해석·예측·투자 조언 포함 금지.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

_STOCK_CACHE_DIR = Path("data/raw/stock")


def _today_str() -> str:
    return date.today().isoformat()


def _cache_path(ticker: str) -> Path:
    return _STOCK_CACHE_DIR / f"{ticker}_{_today_str()}.json"


def _read_cache(ticker: str) -> Any | None:
    path = _cache_path(ticker)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def _write_cache(ticker: str, data: Any) -> None:
    _STOCK_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _cache_path(ticker).write_text(
        json.dumps(data, ensure_ascii=False), encoding="utf-8"
    )


def fetch_stock_ohlc(ticker: str, period_days: int = 365) -> list[dict]:
    """KRX 일봉 OHLC 를 반환한다. 캐시 우선(일일 1회).

    ticker: 6자리 종목코드 (예: "005930")
    반환: [{date, open, high, low, close, volume}, ...]
    """
    cached = _read_cache(ticker)
    if cached is not None:
        return cached

    try:
        import FinanceDataReader as fdr  # noqa: N813
    except ImportError as exc:
        raise RuntimeError(
            "finance-datareader 가 설치되지 않았습니다: uv add finance-datareader"
        ) from exc

    end = date.today()
    start = end - timedelta(days=period_days)
    df = fdr.DataReader(ticker, start.isoformat(), end.isoformat())

    rows: list[dict] = []
    for idx, row in df.iterrows():
        rows.append(
            {
                "date": str(idx)[:10],
                "open": int(row.get("Open", 0)),
                "high": int(row.get("High", 0)),
                "low": int(row.get("Low", 0)),
                "close": int(row.get("Close", 0)),
                "volume": int(row.get("Volume", 0)),
            }
        )

    _write_cache(ticker, rows)
    return rows


def compute_stock_summary(rows: list[dict], company: str, ticker: str) -> dict:
    """OHLC 리스트에서 요약 통계를 계산한다. 사실만, 해석 없음."""
    if not rows:
        return {"found": False, "reason": f"{company}({ticker}) 주가 데이터 없음"}

    closes = [r["close"] for r in rows if r["close"] > 0]
    if not closes:
        return {"found": False, "reason": f"{company}({ticker}) 종가 데이터 없음"}

    latest = rows[-1]
    prev = rows[-2] if len(rows) >= 2 else rows[-1]

    change = latest["close"] - prev["close"]
    change_pct = round(change / prev["close"] * 100, 2) if prev["close"] else None

    return {
        "found": True,
        "company": company,
        "ticker": ticker,
        "date": latest["date"],
        "close": latest["close"],
        "change": change,
        "change_pct": change_pct,
        "high_52w": max(closes),
        "low_52w": min(closes),
        "ohlc": rows,
    }
