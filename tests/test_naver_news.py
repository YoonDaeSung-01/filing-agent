"""네이버 뉴스 검색 — HTML 정제·캐싱·오류 처리 검증(네트워크 모킹)."""

import pytest

from filing_agent.config import Settings
from filing_agent.platform.news import naver_news


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
    base = dict(dart_api_key="x", naver_client_id="id", naver_client_secret="secret")
    base.update(over)
    return Settings(**base)


_RAW = {
    "items": [
        {
            "title": "&lt;b&gt;삼성&lt;/b&gt;전자, 성과급 산정기준 변경",
            "originallink": "https://example.com/1",
            "link": "https://news.naver.com/1",
            "description": "&lt;b&gt;삼성전자&lt;/b&gt;가 발표했다.",
            "pubDate": "Wed, 01 Jul 2026 14:18:00 +0900",
        }
    ]
}


def test_fetch_news_strips_html_and_entities(monkeypatch, tmp_path):
    monkeypatch.setattr(naver_news, "_CACHE_DIR", tmp_path)
    monkeypatch.setattr(naver_news.httpx, "get", lambda *a, **k: _FakeResp(_RAW))

    items = naver_news.fetch_news("삼성전자", settings=_cfg())
    assert len(items) == 1
    assert items[0]["title"] == "삼성전자, 성과급 산정기준 변경"
    assert items[0]["description"] == "삼성전자가 발표했다."
    assert items[0]["link"] == "https://example.com/1"
    assert items[0]["source"] == "네이버 뉴스"


def test_missing_keys_raises(monkeypatch, tmp_path):
    monkeypatch.setattr(naver_news, "_CACHE_DIR", tmp_path)
    with pytest.raises(naver_news.NaverNewsError):
        naver_news.fetch_news("삼성전자", settings=_cfg(naver_client_id="", naver_client_secret=""))


def test_cache_reused_within_ttl(monkeypatch, tmp_path):
    monkeypatch.setattr(naver_news, "_CACHE_DIR", tmp_path)
    calls = {"n": 0}

    def fake_get(*a, **k):
        calls["n"] += 1
        return _FakeResp(_RAW)

    monkeypatch.setattr(naver_news.httpx, "get", fake_get)

    naver_news.fetch_news("삼성전자", settings=_cfg())
    naver_news.fetch_news("삼성전자", settings=_cfg())
    assert calls["n"] == 1  # 두 번째는 캐시


def test_cache_expires_after_ttl(monkeypatch, tmp_path):
    monkeypatch.setattr(naver_news, "_CACHE_DIR", tmp_path)
    monkeypatch.setattr(naver_news, "_CACHE_TTL_SEC", 0)  # 즉시 만료
    calls = {"n": 0}

    def fake_get(*a, **k):
        calls["n"] += 1
        return _FakeResp(_RAW)

    monkeypatch.setattr(naver_news.httpx, "get", fake_get)

    naver_news.fetch_news("삼성전자", settings=_cfg())
    naver_news.fetch_news("삼성전자", settings=_cfg())
    assert calls["n"] == 2
