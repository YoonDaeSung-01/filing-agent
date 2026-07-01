"""한투 KIS 토큰 클라이언트 — 캐싱·오류 처리 검증(네트워크 모킹)."""

import json
import time

import pytest

from filing_agent.config import Settings
from filing_agent.platform.market import kis_client


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
    base = dict(
        dart_api_key="x",
        kis_app_key="k",
        kis_app_secret="s",
        kis_account_no="50000000",
    )
    base.update(over)
    return Settings(**base)


def test_token_requested_then_cached(monkeypatch, tmp_path):
    """첫 호출은 네트워크, 두 번째는 캐시(재호출 없음)."""
    monkeypatch.setattr(kis_client, "_TOKEN_CACHE", tmp_path / "tok.json")
    calls: list[str] = []

    def fake_post(url, json, timeout):  # noqa: A002 - httpx 시그니처
        calls.append(url)
        return _FakeResp({"access_token": "ABC", "expires_in": 86400})

    monkeypatch.setattr(kis_client.httpx, "post", fake_post)

    assert kis_client.get_access_token(_cfg()) == "ABC"
    assert kis_client.get_access_token(_cfg()) == "ABC"
    assert len(calls) == 1  # 두 번째는 캐시


def test_expired_cache_refetches(monkeypatch, tmp_path):
    cache = tmp_path / "tok.json"
    cache.write_text(json.dumps({"access_token": "OLD", "expires_at": time.time() - 10}))
    monkeypatch.setattr(kis_client, "_TOKEN_CACHE", cache)
    monkeypatch.setattr(
        kis_client.httpx,
        "post",
        lambda url, json, timeout: _FakeResp({"access_token": "NEW", "expires_in": 86400}),
    )
    assert kis_client.get_access_token(_cfg()) == "NEW"


def test_missing_keys_raises(monkeypatch, tmp_path):
    monkeypatch.setattr(kis_client, "_TOKEN_CACHE", tmp_path / "tok.json")
    with pytest.raises(kis_client.KisApiError):
        kis_client.get_access_token(_cfg(kis_app_key="", kis_app_secret=""))


def test_no_access_token_in_response_raises(monkeypatch, tmp_path):
    monkeypatch.setattr(kis_client, "_TOKEN_CACHE", tmp_path / "tok.json")
    monkeypatch.setattr(
        kis_client.httpx,
        "post",
        lambda url, json, timeout: _FakeResp({"error_code": "EGW00133"}),
    )
    with pytest.raises(kis_client.KisApiError):
        kis_client.get_access_token(_cfg())


def test_force_ignores_valid_cache(monkeypatch, tmp_path):
    cache = tmp_path / "tok.json"
    cache.write_text(json.dumps({"access_token": "OLD", "expires_at": time.time() + 9999}))
    monkeypatch.setattr(kis_client, "_TOKEN_CACHE", cache)
    monkeypatch.setattr(
        kis_client.httpx,
        "post",
        lambda url, json, timeout: _FakeResp({"access_token": "FORCED", "expires_in": 86400}),
    )
    assert kis_client.get_access_token(_cfg(), force=True) == "FORCED"
