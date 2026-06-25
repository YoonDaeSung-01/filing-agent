"""헬스체크 엔드포인트 — 키 없이도 통과해야 한다."""

from fastapi.testclient import TestClient

from filing_agent.api.main import app


def test_health_returns_ok() -> None:
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
