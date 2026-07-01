"""네이버 뉴스 검색 API — 종목명으로 최신 기사 조회 + 짧은 TTL 캐싱.

규칙:
- 비밀값(client_id/secret)은 Settings(.env)에서만. 하드코딩·로깅 금지.
- 사실 요약 데이터만 반환한다. 호재/악재 판정·매수신호화 없음(투자 조언 아님).
- 응답 title/description 은 검색어를 <b> 태그로 감싸 오므로 HTML 태그·엔티티를 제거한다.
"""

from __future__ import annotations

import html
import json
import re
import time
from pathlib import Path
from typing import Any

import httpx

from filing_agent.config import Settings, get_settings

_NEWS_URL = "https://openapi.naver.com/v1/search/news.json"
_TIMEOUT_SEC = 10.0
_CACHE_DIR = Path("data/raw/news")
_CACHE_TTL_SEC = 600  # 10분 — 네이버 일일 한도(25,000)는 넉넉하지만 과호출 방지

_TAG_RE = re.compile(r"<[^>]+>")


class NaverNewsError(RuntimeError):
    """네이버 뉴스 API 호출 실패(키 미설정 등)."""


def _clean(text: str) -> str:
    # 언이스케이프 먼저: 네이버는 강조어를 리터럴 <b> 태그로 감싸 보내지만,
    # 방어적으로 &lt;b&gt; 처럼 이스케이프된 형태가 와도 태그로 인식해 제거하려면
    # 태그 제거보다 언이스케이프를 먼저 해야 한다.
    return _TAG_RE.sub("", html.unescape(text)).strip()


def _cache_path(query: str) -> Path:
    safe = re.sub(r"[^\w가-힣]", "_", query)
    return _CACHE_DIR / f"{safe}.json"


def _read_cache(query: str) -> list[dict] | None:
    path = _cache_path(query)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if time.time() - payload.get("cached_at", 0) > _CACHE_TTL_SEC:
        return None
    return payload.get("items")  # type: ignore[no-any-return]


def _write_cache(query: str, items: list[dict]) -> None:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _cache_path(query).write_text(
        json.dumps({"cached_at": time.time(), "items": items}, ensure_ascii=False),
        encoding="utf-8",
    )


def fetch_news(query: str, display: int = 10, settings: Settings | None = None) -> list[dict]:
    """종목명(또는 임의 쿼리)로 최신 뉴스를 조회한다. 사실 요약만(호재/악재 판정 없음).

    반환: [{title, link, description, pub_date, source}, ...] (최신순)
    """
    cached = _read_cache(query)
    if cached is not None:
        return cached

    cfg = settings or get_settings()
    if not cfg.naver_client_id or not cfg.naver_client_secret:
        raise NaverNewsError("네이버 API 키가 설정되지 않았습니다(.env: NAVER_CLIENT_ID/SECRET).")

    headers = {
        "X-Naver-Client-Id": cfg.naver_client_id,
        "X-Naver-Client-Secret": cfg.naver_client_secret,
    }
    params = {"query": query, "display": display, "sort": "date"}
    resp = httpx.get(_NEWS_URL, headers=headers, params=params, timeout=_TIMEOUT_SEC)
    resp.raise_for_status()
    payload: dict[str, Any] = resp.json()

    items = [
        {
            "title": _clean(it.get("title", "")),
            "link": it.get("originallink") or it.get("link", ""),
            "description": _clean(it.get("description", "")),
            "pub_date": it.get("pubDate", ""),
            "source": "네이버 뉴스",
        }
        for it in payload.get("items", [])
    ]
    _write_cache(query, items)
    return items
