import uuid
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_
from app.auth import WorkspaceContext, get_workspace_context
from app.models.account import Account
from app.schemas.account import AccountListItem, AccountDetail
from app.schemas.dashboard import DashboardAccount, DashboardSignal
from app.services.scoring import (
    compute_account_score,
    opportunity_probability,
    signal_score_contribution,
    days_ago,
    enhance_why_now,
)

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("/dashboard")
def dashboard(ctx: WorkspaceContext = Depends(get_workspace_context)):
    db = ctx.db
    accounts = db.scalars(
        select(Account).where(Account.workspace_id == ctx.workspace_id)
    ).all()
    result = []
    for acct in accounts:
        score = compute_account_score(acct.signals)
        prob = opportunity_probability(score)
        signals_out = []
        for s in sorted(acct.signals, key=lambda x: x.occurred_at, reverse=True):
            signals_out.append(DashboardSignal(
                type=s.type,
                description=s.title,
                date=s.occurred_at.strftime("%Y-%m-%d"),
                daysAgo=days_ago(s.occurred_at),
                scoreContribution=signal_score_contribution(s.type, s.occurred_at),
                interpretation=s.summary,
            ))
        result.append(DashboardAccount(
            id=acct.id,
            name=acct.name,
            website=acct.domain,
            industry=acct.industry,
            employeeCount=acct.employee_count,
            fundingStage=acct.funding_stage,
            status=acct.status,
            opportunityScore=score,
            opportunityProbability=prob,
            signals=signals_out,
            whyNow=enhance_why_now(acct.why_now, acct.signals),
            recommendedBuyerPersona=acct.recommended_buyer_persona or [],
            suggestedOutreachAngle=acct.suggested_outreach_angle,
            strategicIntelligence=acct.strategic_intelligence,
        ))
    result.sort(key=lambda x: x.opportunityScore, reverse=True)
    return {"data": result}


@router.get("")
def list_accounts(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    sort_by: Literal["name", "created_at"] = Query(default="created_at"),
    order: Literal["asc", "desc"] = Query(default="desc"),
    industry: str | None = Query(default=None),
    search: str | None = Query(default=None),
    ctx: WorkspaceContext = Depends(get_workspace_context),
):
    db = ctx.db
    query = select(Account).where(Account.workspace_id == ctx.workspace_id)
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
def get_account(
    account_id: uuid.UUID,
    ctx: WorkspaceContext = Depends(get_workspace_context),
):
    db = ctx.db
    # Must scope by workspace_id — db.get() alone would leak cross-workspace data
    account = db.scalar(
        select(Account).where(
            Account.id == account_id,
            Account.workspace_id == ctx.workspace_id,
        )
    )
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return {"data": AccountDetail.model_validate(account)}
