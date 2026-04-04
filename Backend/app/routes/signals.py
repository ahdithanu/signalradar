"""Signal endpoints including evidence detail.

The evidence endpoint returns the full raw event data that generated a signal,
providing explainability for why a signal was created.
"""

import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.auth import WorkspaceContext, get_workspace_context
from app.models.signal import Signal
from app.models.raw_event import RawEvent
from app.models.account_source import AccountSource
from app.services.scoring import signal_score_contribution, days_ago

router = APIRouter(prefix="/signals", tags=["signals"])


# ── Response schemas ─────────────────────────────────────────────────────

class SignalListItem(BaseModel):
    id: uuid.UUID
    accountId: uuid.UUID
    type: str
    title: str
    summary: str | None
    occurredAt: str
    daysAgo: int
    scoreContribution: float
    hasEvidence: bool

    model_config = {"from_attributes": True}


class SignalEvidence(BaseModel):
    """Full explainability for a signal — what raw data generated it."""
    signalId: uuid.UUID
    signalType: str
    signalTitle: str
    signalSummary: str | None
    occurredAt: str
    scoreContribution: float

    # Source metadata
    sourceType: str | None = None
    sourceUrl: str | None = None

    # Raw event evidence
    rawEventId: uuid.UUID | None = None
    eventType: str | None = None
    rawPayload: dict[str, Any] | None = None
    fetchedAt: str | None = None
    externalId: str | None = None
    status: str | None = None
    statusDetail: str | None = None

    # Extracted fields for positioning_shift signals
    pageUrl: str | None = None
    previousText: str | None = None
    currentText: str | None = None
    changedSections: list[str] | None = None
    extractedKeywords: list[str] | None = None
    diffPercentage: float | None = None
    detectedShift: str | None = None
    confidenceScore: float | None = None


# ── Endpoints ────────────────────────────────────────────────────────────

@router.get("")
def list_signals(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    account_id: uuid.UUID | None = Query(default=None),
    signal_type: str | None = Query(default=None),
    sort_by: Literal["occurred_at", "created_at"] = Query(default="occurred_at"),
    order: Literal["asc", "desc"] = Query(default="desc"),
    ctx: WorkspaceContext = Depends(get_workspace_context),
):
    db = ctx.db
    query = select(Signal).where(Signal.workspace_id == ctx.workspace_id)

    if account_id:
        query = query.where(Signal.account_id == account_id)
    if signal_type:
        query = query.where(Signal.type == signal_type)

    sort_col = getattr(Signal, sort_by)
    query = query.order_by(sort_col.desc() if order == "desc" else sort_col.asc())

    total = db.scalar(select(func.count()).select_from(query.subquery()))
    rows = db.scalars(query.offset(offset).limit(limit)).all()

    items = []
    for s in rows:
        items.append(SignalListItem(
            id=s.id,
            accountId=s.account_id,
            type=s.type,
            title=s.title,
            summary=s.summary,
            occurredAt=s.occurred_at.isoformat(),
            daysAgo=days_ago(s.occurred_at),
            scoreContribution=signal_score_contribution(s.type, s.occurred_at),
            hasEvidence=s.raw_event_id is not None,
        ))

    return {
        "data": items,
        "total": total or 0,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{signal_id}")
def get_signal(
    signal_id: uuid.UUID,
    ctx: WorkspaceContext = Depends(get_workspace_context),
):
    db = ctx.db
    signal = db.scalar(
        select(Signal).where(
            Signal.id == signal_id,
            Signal.workspace_id == ctx.workspace_id,
        )
    )
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")

    return {
        "data": SignalListItem(
            id=signal.id,
            accountId=signal.account_id,
            type=signal.type,
            title=signal.title,
            summary=signal.summary,
            occurredAt=signal.occurred_at.isoformat(),
            daysAgo=days_ago(signal.occurred_at),
            scoreContribution=signal_score_contribution(signal.type, signal.occurred_at),
            hasEvidence=signal.raw_event_id is not None,
        )
    }


@router.get("/{signal_id}/evidence")
def get_signal_evidence(
    signal_id: uuid.UUID,
    ctx: WorkspaceContext = Depends(get_workspace_context),
):
    """Return full evidence chain for a signal: signal → raw_event → account_source.

    This is the explainability endpoint — it tells the user exactly
    what data generated a signal and why.
    """
    db = ctx.db
    signal = db.scalar(
        select(Signal).where(
            Signal.id == signal_id,
            Signal.workspace_id == ctx.workspace_id,
        )
    )
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")

    evidence = SignalEvidence(
        signalId=signal.id,
        signalType=signal.type,
        signalTitle=signal.title,
        signalSummary=signal.summary,
        occurredAt=signal.occurred_at.isoformat(),
        scoreContribution=signal_score_contribution(signal.type, signal.occurred_at),
    )

    if not signal.raw_event_id:
        # Seed signal — no raw event evidence
        return {"data": evidence}

    raw_event = db.get(RawEvent, signal.raw_event_id)
    if raw_event:
        evidence.rawEventId = raw_event.id
        evidence.eventType = raw_event.event_type
        evidence.rawPayload = raw_event.raw_payload
        evidence.fetchedAt = raw_event.fetched_at.isoformat() if raw_event.fetched_at else None
        evidence.externalId = raw_event.external_id
        evidence.status = raw_event.status
        evidence.statusDetail = raw_event.status_detail

        # Extract structured fields from payload
        payload = raw_event.raw_payload or {}
        evidence.pageUrl = payload.get("page_url")
        evidence.previousText = payload.get("previous_text")
        evidence.currentText = payload.get("current_text")
        evidence.changedSections = payload.get("changed_sections")
        evidence.extractedKeywords = payload.get("extracted_keywords")
        evidence.detectedShift = payload.get("detected_shift")

        diff_pct = payload.get("diff_percentage")
        if diff_pct is not None:
            try:
                evidence.diffPercentage = float(diff_pct)
            except (TypeError, ValueError):
                pass

        # Compute confidence based on signal type and evidence quality
        evidence.confidenceScore = _compute_confidence(signal.type, payload)

        # Source metadata
        source = db.get(AccountSource, raw_event.account_source_id)
        if source:
            evidence.sourceType = source.source_type
            evidence.sourceUrl = source.source_url

    return {"data": evidence}


def _compute_confidence(signal_type: str, payload: dict) -> float:
    """Compute a 0.0–1.0 confidence score based on evidence quality.

    Rules-based, not ML. Higher confidence when:
    - More fields are populated
    - Change is larger (higher diff_percentage)
    - Multiple GTM keywords detected
    - Change significance is "high"
    """
    score = 0.5  # baseline

    if signal_type == "positioning_shift":
        significance = payload.get("change_significance", "")
        if significance == "high":
            score += 0.2
        elif significance == "medium":
            score += 0.1

        diff_pct = payload.get("diff_percentage")
        if diff_pct is not None:
            try:
                pct = float(diff_pct)
                if pct >= 0.5:
                    score += 0.15
                elif pct >= 0.3:
                    score += 0.1
            except (TypeError, ValueError):
                pass

        keywords = payload.get("extracted_keywords") or []
        if len(keywords) >= 4:
            score += 0.1
        elif len(keywords) >= 2:
            score += 0.05

        if payload.get("previous_text") and payload.get("current_text"):
            score += 0.05  # before/after comparison available

    elif signal_type == "funding":
        if payload.get("money_raised_usd"):
            score += 0.2
        if payload.get("round_type"):
            score += 0.1
        if payload.get("announced_on"):
            score += 0.1

    return min(round(score, 2), 1.0)
