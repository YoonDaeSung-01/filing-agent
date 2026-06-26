"""관측(Observability) — Langfuse 트레이싱을 선택적으로 켠다.

설계 원칙(Phase 6):
- **선택적**: 키가 없으면 아무것도 하지 않는다(no-op). 앱·테스트는 키 없이 그대로 동작한다.
- **이중 경로**: 에이전트 그래프(ChatLiteLLM)는 LangChain CallbackHandler 로, 직접 LiteLLM
  호출(임베딩·완성)은 litellm 콜백으로 잡는다.
- **비밀값**: 키는 Settings(=.env)에서만 읽는다. 로깅하지 않는다.

⚠️ 키 전파: pydantic-settings 는 .env 를 Settings 객체로만 읽고 os.environ 에는 넣지 않는다.
   Langfuse SDK / litellm 콜백은 os.environ 의 LANGFUSE_* 를 읽으므로, 활성화 시 Settings 값을
   os.environ 으로 전파해야 트레이싱이 실제로 켜진다(안 그러면 에러 없이 무음 실패).

langfuse v4(OTEL-native) 기준: litellm 직접 호출은 v2용 "langfuse" 가 아니라
"langfuse_otel" 콜백을 쓴다(v2 API 비호환 회피).
"""

from __future__ import annotations

import logging

from filing_agent.config import Settings, get_settings

logger = logging.getLogger(__name__)

_LITELLM_CALLBACK = "langfuse_otel"


def _enabled(cfg: Settings) -> bool:
    """Langfuse 공개·비밀 키가 둘 다 있으면 True."""
    return bool(cfg.langfuse_public_key and cfg.langfuse_secret_key)


def configure_observability() -> None:
    """앱 시작 시 1회 호출. 키 있을 때만 환경 전파 + litellm 콜백 등록(멱등)."""
    cfg = get_settings()
    if not _enabled(cfg):
        return

    import os

    # .env→Settings→os.environ 전파(Langfuse/litellm 이 환경변수에서 읽음).
    # setdefault: 이미 외부에서 설정한 값이 있으면 존중한다.
    os.environ.setdefault("LANGFUSE_PUBLIC_KEY", cfg.langfuse_public_key)
    os.environ.setdefault("LANGFUSE_SECRET_KEY", cfg.langfuse_secret_key)
    os.environ.setdefault("LANGFUSE_HOST", cfg.langfuse_host)

    import litellm

    existing = list(litellm.callbacks or [])
    if _LITELLM_CALLBACK not in existing:
        litellm.callbacks = [*existing, _LITELLM_CALLBACK]
    logger.info("Langfuse 관측 활성화(host=%s)", cfg.langfuse_host)


def get_langfuse_callbacks() -> list:
    """그래프 invoke 에 넘길 콜백 핸들러 리스트. 키 없으면 [] (no-op)."""
    cfg = get_settings()
    if not _enabled(cfg):
        return []
    from langfuse.langchain import CallbackHandler  # 지연 임포트(키 있을 때만)

    return [CallbackHandler()]  # configure_observability 의 환경 전파로 키를 찾음
