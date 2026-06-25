"""FastAPI 앱 진입점.

이 단계에서는 헬스체크만 노출한다. /ask(걷는 해골)는 Phase B 에서 추가된다.
실행: ``uv run uvicorn filing_agent.api.main:app --reload``
"""

from fastapi import FastAPI

app = FastAPI(
    title="filing-agent",
    description="DART(한국 전자공시) 기반 공시 사실 추출 API. 투자 조언 도구가 아니다.",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
