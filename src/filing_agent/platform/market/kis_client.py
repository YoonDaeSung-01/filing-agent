"""한투 KIS Open API 클라이언트 — 접근 토큰 발급 + 디스크 캐싱.

규칙(CLAUDE.md·플랫폼 계획서 준수):
- 비밀값(app_key/app_secret)은 Settings(.env)에서만 읽는다. **하드코딩·로깅 금지.**
- 토큰은 발급 한도가 있어 반드시 캐싱한다(만료 전 재사용). ★모의투자(vps) 전용★.
- 실패는 예외(KisApiError)로. 응답에 access_token 없으면 코드만 남기고 비밀값은 로깅하지 않는다.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

import httpx

from filing_agent.config import Settings, get_settings

logger = logging.getLogger(__name__)

# 토큰 캐시(프로젝트 루트 기준 상대). 런타임 생성·git 미포함.
_TOKEN_CACHE = Path("data/raw/kis_token.json")
_TIMEOUT_SEC = 10.0
_EXPIRY_BUFFER_SEC = 600  # 만료 10분 전 선제 갱신


class KisApiError(RuntimeError):
    """한투 API 호출 실패(토큰 미발급·키 미설정 등)."""


def get_access_token(settings: Settings | None = None, *, force: bool = False) -> str:
    """유효한 접근 토큰을 반환한다. 캐시 우선(만료 전 재사용). vps 전용.

    force=True 면 캐시를 무시하고 새로 발급한다.
    """
    cfg = settings or get_settings()
    if not force:
        cached = _read_token_cache()
        if cached is not None and _is_valid(cached):
            return str(cached["access_token"])
    return _request_new_token(cfg)


def _read_token_cache() -> dict[str, Any] | None:
    if not _TOKEN_CACHE.exists():
        return None
    try:
        return json.loads(_TOKEN_CACHE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _write_token_cache(data: dict[str, Any]) -> None:
    _TOKEN_CACHE.parent.mkdir(parents=True, exist_ok=True)
    _TOKEN_CACHE.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _is_valid(cached: dict[str, Any]) -> bool:
    return bool(cached.get("access_token")) and time.time() < cached.get("expires_at", 0)


def _request_new_token(cfg: Settings) -> str:
    if not cfg.kis_app_key or not cfg.kis_app_secret:
        raise KisApiError("KIS 키가 설정되지 않았습니다(.env: KIS_APP_KEY/KIS_APP_SECRET).")

    body = {
        "grant_type": "client_credentials",
        "appkey": cfg.kis_app_key,
        "appsecret": cfg.kis_app_secret,
    }
    resp = httpx.post(f"{cfg.kis_base_url}/oauth2/tokenP", json=body, timeout=_TIMEOUT_SEC)
    resp.raise_for_status()
    payload: dict[str, Any] = resp.json()

    token = payload.get("access_token")
    if not token:
        # 비밀값은 남기지 않는다. 식별 가능한 코드만.
        code = payload.get("error_code") or payload.get("rt_cd") or "unknown"
        raise KisApiError(f"토큰 발급 실패(code={code}).")

    expires_in = int(payload.get("expires_in", 86400))
    _write_token_cache(
        {"access_token": token, "expires_at": time.time() + expires_in - _EXPIRY_BUFFER_SEC}
    )
    logger.info("KIS 접근 토큰 발급 완료(vps). 만료 %d초 후.", expires_in)
    return str(token)
