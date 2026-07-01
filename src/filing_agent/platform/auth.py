"""JWT 인증 — 비밀번호 해싱(bcrypt) + 토큰 발급/검증.

규칙: JWT_SECRET 등 비밀값은 Settings(.env)에서만. 비밀번호는 평문 저장·로깅 금지.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from filing_agent.config import Settings, get_settings
from filing_agent.platform.db import get_session
from filing_agent.platform.models import User

_ALGORITHM = "HS256"
_BCRYPT_MAX_BYTES = 72  # bcrypt 알고리즘 자체 한도

_bearer = HTTPBearer(auto_error=False)
_BearerDep = Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]
_DbDep = Annotated[Session, Depends(get_session)]


def hash_password(raw: str) -> str:
    truncated = raw.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    return bcrypt.hashpw(truncated, bcrypt.gensalt()).decode("utf-8")


def verify_password(raw: str, hashed: str) -> bool:
    truncated = raw.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    try:
        return bcrypt.checkpw(truncated, hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(email: str, settings: Settings | None = None) -> str:
    cfg = settings or get_settings()
    if not cfg.jwt_secret:
        raise RuntimeError("JWT_SECRET 이 설정되지 않았습니다(.env).")
    expire = datetime.now(UTC) + timedelta(minutes=cfg.jwt_expire_min)
    payload: dict[str, Any] = {"sub": email, "exp": expire}
    return jwt.encode(payload, cfg.jwt_secret, algorithm=_ALGORITHM)


def decode_access_token(token: str, settings: Settings | None = None) -> str:
    """토큰에서 email(sub)을 반환한다. 유효하지 않으면 JWTError."""
    cfg = settings or get_settings()
    payload = jwt.decode(token, cfg.jwt_secret, algorithms=[_ALGORITHM])
    return str(payload["sub"])


def get_current_user(creds: _BearerDep, db: _DbDep) -> User:
    """FastAPI Depends — Authorization: Bearer <token> 검증 후 User 반환."""
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="인증이 필요합니다.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if creds is None:
        raise unauthorized
    try:
        email = decode_access_token(creds.credentials)
    except JWTError as exc:
        raise unauthorized from exc

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise unauthorized
    return user
