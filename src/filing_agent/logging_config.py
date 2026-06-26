"""전역 로깅 설정 — 표준 logging 사용(추가 의존성 없음).

Langfuse(Phase 6) 도입 전까지 에러·재시도·주요 상태 전이를 콘솔/파일로 남겨
프로덕션 디버깅을 가능하게 한다. 앱 진입점(api.main)에서 1회 호출한다.
"""

from __future__ import annotations

import logging

_CONFIGURED = False


def configure_logging(level: int = logging.INFO) -> None:
    """루트 로거를 1회 구성한다(중복 호출 안전)."""
    global _CONFIGURED
    if _CONFIGURED:
        return
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    _CONFIGURED = True
