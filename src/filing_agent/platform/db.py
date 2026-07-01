"""플랫폼 DB 엔진/세션 — pgvector와 같은 Postgres, 별도 스키마(운영 테이블).

코어(retrieval/ingest)는 raw psycopg를 직접 쓰지만, 플랫폼 계층은 ORM(SQLAlchemy)을
쓴다. 같은 pg_dsn을 재사용하되 SQLAlchemy 방언 접두사(+psycopg)만 붙여 별도
엔진을 구성한다 — 코어가 쓰는 Settings.pg_dsn 값 자체는 건드리지 않는다.
"""

from __future__ import annotations

from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from filing_agent.config import get_settings


class Base(DeclarativeBase):
    pass


def to_sqlalchemy_url(pg_dsn: str) -> str:
    if pg_dsn.startswith("postgresql://"):
        return pg_dsn.replace("postgresql://", "postgresql+psycopg://", 1)
    return pg_dsn


@lru_cache
def get_engine() -> Engine:
    cfg = get_settings()
    return create_engine(to_sqlalchemy_url(cfg.pg_dsn), pool_pre_ping=True)


def get_session() -> Generator[Session, None, None]:
    """FastAPI Depends 용 — 요청마다 세션 열고 끝나면 닫는다."""
    session_factory = sessionmaker(bind=get_engine())
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
