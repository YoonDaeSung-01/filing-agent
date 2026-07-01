"""stock_client — 캐시가 기간(period_days)과 무관하게 정합적인지 검증.

버그 재현: 캐시 키가 ticker만 쓰면, 3년 조회 후 캐시된 데이터를 1주 조회에도
그대로 반환해 729개 같은 엉뚱한 개수가 나온다. 수정: 캐시는 최대기간을 통째로
저장하고, period_days 만큼 슬라이스해서 반환한다.
"""

from datetime import date, timedelta

from filing_agent.ingest import stock_client


def _fake_rows(n_days: int) -> list[dict]:
    today = date.today()
    rows = []
    for i in range(n_days, 0, -1):
        d = today - timedelta(days=i)
        rows.append(
            {"date": d.isoformat(), "open": 100, "high": 100, "low": 100, "close": 100, "volume": 1}
        )
    return rows


def test_different_periods_slice_same_cache(monkeypatch, tmp_path):
    cache_dir = tmp_path / "stock"
    monkeypatch.setattr(stock_client, "_STOCK_CACHE_DIR", cache_dir)

    calls = {"n": 0}

    def fake_download(ticker):
        calls["n"] += 1
        return _fake_rows(1000)

    monkeypatch.setattr(stock_client, "_download_full_history", fake_download)

    long_result = stock_client.fetch_stock_ohlc("005930", period_days=1095)
    short_result = stock_client.fetch_stock_ohlc("005930", period_days=7)

    assert len(long_result) > len(short_result)
    assert len(short_result) <= 8  # 7일 컷오프 근방
    assert calls["n"] == 1  # 두 번째 호출은 캐시 재사용(네트워크 1회만)


def test_cache_persists_across_calls(monkeypatch, tmp_path):
    cache_dir = tmp_path / "stock"
    monkeypatch.setattr(stock_client, "_STOCK_CACHE_DIR", cache_dir)
    monkeypatch.setattr(stock_client, "_download_full_history", lambda ticker: _fake_rows(30))

    r1 = stock_client.fetch_stock_ohlc("005930", period_days=30)
    r2 = stock_client.fetch_stock_ohlc("005930", period_days=30)
    assert r1 == r2
    assert (cache_dir / f"005930_{date.today().isoformat()}.json").exists()


def test_empty_history_returns_empty(monkeypatch, tmp_path):
    cache_dir = tmp_path / "stock"
    monkeypatch.setattr(stock_client, "_STOCK_CACHE_DIR", cache_dir)
    monkeypatch.setattr(stock_client, "_download_full_history", lambda ticker: [])

    assert stock_client.fetch_stock_ohlc("999999", period_days=30) == []


def test_compute_summary_on_empty():
    r = stock_client.compute_stock_summary([], company="테스트", ticker="000000")
    assert r["found"] is False
