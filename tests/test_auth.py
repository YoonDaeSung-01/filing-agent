"""JWT 인증 유틸 — 해싱·토큰 발급/검증 (DB·네트워크 불필요, 순수 로직)."""

from types import SimpleNamespace

import pytest
from jose import JWTError

from filing_agent.platform import auth


def _cfg(**over):
    base = dict(jwt_secret="test-secret", jwt_expire_min=60)
    base.update(over)
    return SimpleNamespace(**base)


def test_hash_and_verify_roundtrip():
    h = auth.hash_password("my-secret-pw")
    assert h != "my-secret-pw"  # 평문 저장 안 함
    assert auth.verify_password("my-secret-pw", h)
    assert not auth.verify_password("wrong-pw", h)


def test_hash_truncates_long_password_safely():
    # bcrypt 자체 72바이트 한도 — 넘어도 예외 없이 안전하게 처리돼야 함
    long_pw = "a" * 200
    h = auth.hash_password(long_pw)
    assert auth.verify_password(long_pw, h)


def test_verify_rejects_garbage_hash():
    assert auth.verify_password("anything", "not-a-valid-bcrypt-hash") is False


def test_token_roundtrip():
    cfg = _cfg()
    token = auth.create_access_token("user@example.com", cfg)
    assert auth.decode_access_token(token, cfg) == "user@example.com"


def test_token_requires_secret():
    cfg = _cfg(jwt_secret="")
    with pytest.raises(RuntimeError):
        auth.create_access_token("user@example.com", cfg)


def test_expired_token_raises():
    cfg = _cfg(jwt_expire_min=-1)  # 이미 만료된 토큰 발급
    token = auth.create_access_token("user@example.com", cfg)
    with pytest.raises(JWTError):
        auth.decode_access_token(token, cfg)


def test_token_wrong_secret_raises():
    token = auth.create_access_token("user@example.com", _cfg(jwt_secret="secret-a"))
    with pytest.raises(JWTError):
        auth.decode_access_token(token, _cfg(jwt_secret="secret-b"))
