"""llm/client.py 재시도/백오프 단위 테스트 — 실제 네트워크·키 불필요."""

from unittest.mock import patch

import pytest

from filing_agent.llm import client


class _Resp:
    """litellm.embedding 응답 모킹."""

    def __init__(self) -> None:
        self.data = [{"embedding": [0.1, 0.2]}]


class FakeSettings:
    embedding_model = "text-embedding-3-small"
    llm_api_key = "dummy"


def test_retry_recovers_after_transient_error() -> None:
    """일시 오류 1회 후 성공하면 재시도로 복구한다(sleep 은 패치)."""
    if not client._RETRYABLE_ERRORS:
        pytest.skip("litellm 재시도 대상 예외 미존재")

    err_cls = client._RETRYABLE_ERRORS[0]
    calls = {"n": 0}

    def flaky(*args, **kwargs):  # noqa: ANN002, ANN003
        calls["n"] += 1
        if calls["n"] == 1:
            try:
                raise err_cls("rate limited")
            except TypeError:
                # 일부 litellm 예외는 추가 인자 필요 → 범용 생성 우회
                raise err_cls(message="rate limited", llm_provider="openai", model="x") from None
        return _Resp()

    with (
        patch.object(client.litellm, "embedding", side_effect=flaky),
        patch.object(client.time, "sleep", return_value=None),
    ):
        out = client.embed(["hi"], FakeSettings())

    assert out == [[0.1, 0.2]]
    assert calls["n"] == 2  # 1회 실패 + 1회 성공


def test_non_retryable_error_propagates_immediately() -> None:
    """일시 오류가 아니면 즉시 전파(재시도 안 함)."""
    with (
        patch.object(client.litellm, "embedding", side_effect=ValueError("bad")),
        patch.object(client.time, "sleep", return_value=None),
    ):
        with pytest.raises(ValueError):
            client.embed(["hi"], FakeSettings())
