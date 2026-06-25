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

    # ── 검색·리랭킹 (Phase 2) ───────────────────────────
    # 후보를 넉넉히 가져와(retrieve_top_n) 리랭커로 재정렬 후 final_top_k 만 LLM 에 전달.
    retrieve_top_n: int = 20     # 벡터/BM25 각각 가져올 후보 수
    final_top_k: int = 5         # 리랭킹 후 LLM 에 넘길 청크 수
    hybrid_enabled: bool = True  # 벡터 + BM25 RRF 융합 사용 여부
    rrf_k: int = 60              # RRF 상수(랭크 융합 평활화)
    rerank_enabled: bool = True  # cross-encoder 리랭킹 사용 여부
    rerank_model: str = "BAAI/bge-reranker-v2-m3"


@lru_cache
def get_settings() -> Settings:
    """캐시된 Settings 싱글턴."""
    return Settings()
