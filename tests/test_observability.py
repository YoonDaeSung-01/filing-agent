"""observability.py 단위 테스트 — 키·네트워크 불필요.

키 없으면 트레이싱이 no-op 인지, 키 있으면(모킹) 핸들러·콜백이 붙는지 검증한다.
실제 Langfuse 연결은 하지 않는다(핸들러 생성을 모킹).
"""

import sys
import types
from unittest.mock import patch

from filing_agent import observability as obs


class FakeSettings:
    """observability 가 읽는 3개 필드만 가진 가짜 설정."""

    def __init__(self, public: str = "", secret: str = "",
                 host: str = "https://cloud.langfuse.com") -> None:
        self.langfuse_public_key = public
        self.langfuse_secret_key = secret
        self.langfuse_host = host


# ── 키 없음 → no-op ───────────────────────────────────────────────────────────
class TestDisabled:
    def test_callbacks_empty_without_keys(self) -> None:
        with patch.object(obs, "get_settings", return_value=FakeSettings()):
            assert obs.get_langfuse_callbacks() == []

    def test_partial_keys_still_disabled(self) -> None:
        # 공개 키만 있고 비밀 키 없으면 비활성
        with patch.object(obs, "get_settings", return_value=FakeSettings(public="pk")):
            assert obs.get_langfuse_callbacks() == []

    def test_configure_noop_without_keys(self) -> None:
        import litellm

        before = list(litellm.callbacks or [])
        with patch.object(obs, "get_settings", return_value=FakeSettings()):
            obs.configure_observability()
        # 콜백 목록이 변하지 않아야 한다
        assert list(litellm.callbacks or []) == before


# ── 키 있음(모킹) → 활성화 ────────────────────────────────────────────────────
class TestEnabled:
    def test_get_callbacks_returns_handler(self) -> None:
        sentinel = object()
        # 지연 임포트되는 langfuse.langchain 모듈을 가짜로 주입(실제 연결 방지)
        fake_mod = types.ModuleType("langfuse.langchain")
        fake_mod.CallbackHandler = lambda: sentinel
        with (
            patch.object(obs, "get_settings",
                         return_value=FakeSettings(public="pk", secret="sk")),
            patch.dict(sys.modules, {"langfuse.langchain": fake_mod}),
        ):
            result = obs.get_langfuse_callbacks()
        assert result == [sentinel]

    def test_configure_propagates_env_and_registers_callback(self) -> None:
        import litellm

        before = list(litellm.callbacks or [])
        env_keys = ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_HOST")
        saved_env = {k: __import__("os").environ.get(k) for k in env_keys}
        os_mod = __import__("os")
        for k in env_keys:
            os_mod.environ.pop(k, None)
        try:
            with patch.object(
                obs, "get_settings",
                return_value=FakeSettings(public="pk", secret="sk", host="https://h"),
            ):
                obs.configure_observability()
            # 환경 전파 확인
            assert os_mod.environ["LANGFUSE_PUBLIC_KEY"] == "pk"
            assert os_mod.environ["LANGFUSE_SECRET_KEY"] == "sk"
            assert os_mod.environ["LANGFUSE_HOST"] == "https://h"
            # litellm 콜백 등록 확인
            assert obs._LITELLM_CALLBACK in (litellm.callbacks or [])
        finally:
            litellm.callbacks = before  # 전역 상태 복원
            for k, v in saved_env.items():
                if v is None:
                    os_mod.environ.pop(k, None)
                else:
                    os_mod.environ[k] = v

    def test_configure_is_idempotent(self) -> None:
        import litellm

        before = list(litellm.callbacks or [])
        env_keys = ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_HOST")
        os_mod = __import__("os")
        saved_env = {k: os_mod.environ.get(k) for k in env_keys}
        for k in env_keys:
            os_mod.environ.pop(k, None)
        try:
            with patch.object(
                obs, "get_settings",
                return_value=FakeSettings(public="pk", secret="sk"),
            ):
                obs.configure_observability()
                obs.configure_observability()  # 두 번 호출
            # 콜백이 중복 등록되지 않아야 한다
            assert (litellm.callbacks or []).count(obs._LITELLM_CALLBACK) == 1
        finally:
            litellm.callbacks = before
            for k, v in saved_env.items():
                if v is None:
                    os_mod.environ.pop(k, None)
                else:
                    os_mod.environ[k] = v
