"""애플리케이션 설정 — .env 에서 비밀값/기본값을 읽는다.

- 필수 키(dart_api_key, llm_api_key)는 .env 에서만 읽는다. 하드코딩·로깅 금지.
- Settings 는 get_settings() 가 처음 호출될 때 생성된다.
  그래야 키가 없는 환경에서도 /health 와 테스트(픽스처 기반)가 통과한다.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── DART ────────────────────────────────────────────
    dart_api_key: str
    dart_report_code: str = "11011"  # 11011=사업보고서
    dart_fs_div: str = "CFS"         # CFS=연결, OFS=별도

    # ── LLM (LiteLLM 게이트웨이) ────────────────────────
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"

    # ── 임베딩 ──────────────────────────────────────────
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536

    # ── 벡터 DB (pgvector) ──────────────────────────────
    pg_dsn: str = "postgresql://filing:filing@localhost:5433/filing_agent"


@lru_cache
def get_settings() -> Settings:
    """캐시된 Settings 싱글턴."""
    return Settings()
