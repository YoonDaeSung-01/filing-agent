# filing-agent 앱 이미지 — uv 기반.
# 의존성 레이어를 소스보다 먼저 빌드해 레이어 캐시 적중률을 높인다.
# (전체 의존성 포함 = torch 포함. 이미지가 크지만 자체 완결·구성 단순 — Phase 6 결정 #4)

FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /app

# 1) 의존성만 설치(프로젝트 자체는 제외). pyproject 의 readme 참조 때문에 README 도 포함.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-install-project --no-dev

# 2) 앱 소스 + 프로젝트 설치
COPY src/ ./src/
RUN uv sync --frozen --no-dev

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "filing_agent.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
