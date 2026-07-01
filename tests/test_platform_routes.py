"""플랫폼 라우터(/auth, /watchlist, /journal) — SQLite 인메모리로 DB 없이 검증.

CLAUDE.md 원칙: 키·DB·실제 모델 없이도 통과해야 한다. 실제 Postgres는
개발 중 수동으로 라이브 검증했다(세션 기록 참조) — 여기 테스트는 회귀 게이트용.
"""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from filing_agent.api.main import app
from filing_agent.platform import auth as auth_mod
from filing_agent.platform.db import Base, get_session


@pytest.fixture()
def client(monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine)

    def override_get_session():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_session] = override_get_session
    fake_settings = SimpleNamespace(jwt_secret="test-secret", jwt_expire_min=60)
    monkeypatch.setattr(auth_mod, "get_settings", lambda: fake_settings)

    yield TestClient(app)

    app.dependency_overrides.clear()


def _register(client, username="user1", password="test-pw-12345", name="테스터") -> str:
    r = client.post(
        "/auth/register", json={"username": username, "name": name, "password": password}
    )
    assert r.status_code == 200, r.text
    return str(r.json()["access_token"])


def test_register_then_me(client):
    token = _register(client)
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["username"] == "user1"
    assert r.json()["name"] == "테스터"


def test_register_duplicate_username_409(client):
    _register(client)
    r = client.post(
        "/auth/register",
        json={"username": "user1", "name": "다른사람", "password": "another-pw-123"},
    )
    assert r.status_code == 409


def test_register_short_password_400(client):
    r = client.post(
        "/auth/register", json={"username": "user2", "name": "테스터", "password": "short"}
    )
    assert r.status_code == 400


def test_login_success_and_wrong_password(client):
    _register(client, username="loginuser", password="correct-pw-123")
    ok = client.post("/auth/login", json={"username": "loginuser", "password": "correct-pw-123"})
    assert ok.status_code == 200
    bad = client.post("/auth/login", json={"username": "loginuser", "password": "wrong-pw-123"})
    assert bad.status_code == 401


def test_watchlist_requires_auth(client):
    assert client.get("/watchlist").status_code == 401


def test_watchlist_crud(client):
    token = _register(client)
    headers = {"Authorization": f"Bearer {token}"}

    add = client.post(
        "/watchlist", json={"company": "삼성전자", "ticker": "005930"}, headers=headers
    )
    assert add.status_code == 201
    item_id = add.json()["id"]

    listed = client.get("/watchlist", headers=headers)
    assert listed.status_code == 200
    assert listed.json()[0]["company"] == "삼성전자"

    deleted = client.delete(f"/watchlist/{item_id}", headers=headers)
    assert deleted.status_code == 204
    assert client.get("/watchlist", headers=headers).json() == []


def test_watchlist_duplicate_company_409(client):
    token = _register(client)
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/watchlist", json={"company": "삼성전자"}, headers=headers)
    dup = client.post("/watchlist", json={"company": "삼성전자"}, headers=headers)
    assert dup.status_code == 409


def test_delete_others_watchlist_404(client):
    token_a = _register(client, username="userA")
    token_b = _register(client, username="userB")
    add = client.post(
        "/watchlist", json={"company": "삼성전자"}, headers={"Authorization": f"Bearer {token_a}"}
    )
    item_id = add.json()["id"]
    # b가 a의 관심종목을 지우려 하면 404(존재 은닉 — 소유권 검증)
    r = client.delete(f"/watchlist/{item_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert r.status_code == 404


def test_journal_create_and_list(client):
    token = _register(client)
    headers = {"Authorization": f"Bearer {token}"}
    add = client.post(
        "/journal",
        json={"company": "삼성전자", "side": "buy", "qty": 1, "price": 320000, "reason": "테스트"},
        headers=headers,
    )
    assert add.status_code == 201

    listed = client.get("/journal", headers=headers)
    assert listed.status_code == 200
    assert listed.json()[0]["reason"] == "테스트"


def test_journal_invalid_side_400(client):
    token = _register(client)
    r = client.post(
        "/journal",
        json={"company": "삼성전자", "side": "hold", "qty": 1},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 400
