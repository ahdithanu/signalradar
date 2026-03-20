import uuid
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.account import Account
from app.schemas.account import AccountListItem, AccountDetail
router = APIRouter(prefix="/accounts", tags=["accounts"])
@router.get("")
def list_accounts(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    sort_by: Literal["name", "created_at"] = Query(default="created_at"),
    order: Literal["asc", "desc"] = Query(default="desc"),
    industry: str | None = Query(default=None),
    search: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    query = select(Account)
    if industry:
        query = query.where(Account.industry == industry)
    if search:
        pattern = f"%{search}%"
        query = query.where(
            or_(
                Account.name.ilike(pattern),
                Account.domain.ilike(pattern),
            )
        )
    sort_col = getattr(Account, sort_by)
    query = query.order_by(sort_col.desc() if order == "desc" else sort_col.asc())
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    rows = db.scalars(query.offset(offset).limit(limit)).all()
    return {
        "data": [AccountListItem.model_validate(r) for r in rows],
        "total": total or 0,
        "limit": limit,
        "offset": offset,
    }
@router.get("/{account_id}")
def get_account(account_id: uuid.UUID, db: Session = Depends(get_db)):
    account = db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return {"data": AccountDetail.model_validate(account)}
