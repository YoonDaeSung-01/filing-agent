"""애플리케이션 설정 — .env 에서 비밀값/기본값을 읽는다.

- DART_API_KEY 는 필수이며 .env(또는 환경변수)에서만 읽는다. 하드코딩·로깅 금지.
- Settings 는 import 시점이 아니라 get_settings() 가 처음 호출될 때 생성된다.
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

    # 필수: OpenDART 인증키 (.env 의 DART_API_KEY 로 주입)
    dart_api_key: str
    # 보고서 코드 (11011 = 사업보고서/연간)
    dart_report_code: str = "11011"
    # 재무제표 구분 기본값 (CFS = 연결, OFS = 별도)
    dart_fs_div: str = "CFS"


@lru_cache
def get_settings() -> Settings:
    """캐시된 Settings 싱글턴.

    키가 없으면 바로 이 호출에서 pydantic ValidationError 가 발생한다(라우트 단에서 처리).
    """
    return Settings()
