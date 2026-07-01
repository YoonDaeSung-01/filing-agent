"""플랫폼 API 라우터 — 인증(/auth) + 관심종목(/watchlist) + 매매일지(/journal).

DB 영속화 계층. 모의 체결 자체는 한투 vps가 정답 소스(api/main.py의 /paper/*).
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from filing_agent.platform.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from filing_agent.platform.db import get_session
from filing_agent.platform.models import TradeJournalEntry, User, WatchlistItem

router = APIRouter()

_DbDep = Annotated[Session, Depends(get_session)]
_CurrentUser = Annotated[User, Depends(get_current_user)]


# ── 인증 ─────────────────────────────────────────────────────────────────────


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    name: str = Field(min_length=1, max_length=100)
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/auth/register", response_model=TokenResponse)
def register(req: RegisterRequest, db: _DbDep) -> TokenResponse:
    if len(req.password) < 8:
        raise HTTPException(status_code=400, detail="비밀번호는 8자 이상이어야 합니다.")
    user = User(username=req.username, name=req.name, pw_hash=hash_password(req.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="이미 등록된 아이디입니다.") from exc
    return TokenResponse(access_token=create_access_token(req.username))


@router.post("/auth/login", response_model=TokenResponse)
def login(req: LoginRequest, db: _DbDep) -> TokenResponse:
    user = db.query(User).filter(User.username == req.username).first()
    if user is None or not verify_password(req.password, user.pw_hash):
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 올바르지 않습니다.")
    return TokenResponse(access_token=create_access_token(req.username))


@router.get("/auth/me")
def me(user: _CurrentUser) -> dict[str, Any]:
    return {"username": user.username, "name": user.name, "created_at": user.created_at.isoformat()}


# ── 관심종목 ─────────────────────────────────────────────────────────────────


class WatchlistCreate(BaseModel):
    company: str
    ticker: str | None = None
    memo: str | None = None


@router.get("/watchlist")
def list_watchlist(user: _CurrentUser, db: _DbDep) -> list[dict[str, Any]]:
    items = (
        db.query(WatchlistItem)
        .filter(WatchlistItem.user_id == user.id)
        .order_by(WatchlistItem.created_at.desc())
        .all()
    )
    return [
        {
            "id": i.id,
            "company": i.company,
            "ticker": i.ticker,
            "memo": i.memo,
            "created_at": i.created_at.isoformat(),
        }
        for i in items
    ]


@router.post("/watchlist", status_code=status.HTTP_201_CREATED)
def add_watchlist(req: WatchlistCreate, user: _CurrentUser, db: _DbDep) -> dict[str, Any]:
    item = WatchlistItem(user_id=user.id, company=req.company, ticker=req.ticker, memo=req.memo)
    db.add(item)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="이미 관심종목에 있습니다.") from exc
    db.refresh(item)
    return {"id": item.id, "company": item.company}


@router.delete("/watchlist/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_watchlist(item_id: int, user: _CurrentUser, db: _DbDep) -> None:
    item = (
        db.query(WatchlistItem)
        .filter(WatchlistItem.id == item_id, WatchlistItem.user_id == user.id)
        .first()
    )
    if item is None:
        raise HTTPException(status_code=404, detail="관심종목을 찾을 수 없습니다.")
    db.delete(item)
    db.commit()


# ── 매매일지 ─────────────────────────────────────────────────────────────────


class JournalCreate(BaseModel):
    company: str
    side: str  # "buy" | "sell"
    qty: int
    price: int = 0
    reason: str = ""


@router.get("/journal")
def list_journal(user: _CurrentUser, db: _DbDep) -> list[dict[str, Any]]:
    entries = (
        db.query(TradeJournalEntry)
        .filter(TradeJournalEntry.user_id == user.id)
        .order_by(TradeJournalEntry.created_at.desc())
        .all()
    )
    return [
        {
            "id": e.id,
            "company": e.company,
            "side": e.side,
            "qty": e.qty,
            "price": e.price,
            "reason": e.reason,
            "created_at": e.created_at.isoformat(),
        }
        for e in entries
    ]


@router.post("/journal", status_code=status.HTTP_201_CREATED)
def add_journal(req: JournalCreate, user: _CurrentUser, db: _DbDep) -> dict[str, Any]:
    if req.side not in ("buy", "sell"):
        raise HTTPException(status_code=400, detail=f"잘못된 side: {req.side!r}")
    entry = TradeJournalEntry(
        user_id=user.id,
        company=req.company,
        side=req.side,
        qty=req.qty,
        price=req.price,
        reason=req.reason,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return {"id": entry.id}
