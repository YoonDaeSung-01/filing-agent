from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context
from filing_agent.config import get_settings
from filing_agent.platform import models  # noqa: F401 — Base.metadata 등록을 위해 임포트
from filing_agent.platform.db import Base, to_sqlalchemy_url

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# .env 의 pg_dsn 을 그대로 재사용(별도 alembic 전용 설정 파일 두지 않음).
config.set_main_option("sqlalchemy.url", to_sqlalchemy_url(get_settings().pg_dsn))

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# 코어(ingest/indexer.py)가 raw psycopg로 직접 관리하는 pgvector 테이블은
# SQLAlchemy Base.metadata 밖에 있다 — autogenerate가 매번 "제거 대상"으로
# 오인식해 위험한 DROP을 생성하지 않도록 비교 대상에서 제외한다.
_CORE_OWNED_TABLES = {"filing_chunks"}


def include_object(object, name, type_, reflected, compare_to):  # noqa: A002
    if type_ == "table" and name in _CORE_OWNED_TABLES:
        return False
    if type_ == "index" and getattr(object, "table", None) is not None:
        if object.table.name in _CORE_OWNED_TABLES:
            return False
    return True

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
