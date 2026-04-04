"""Admin endpoints — ingestion observability.

GET /admin/ingestion-runs — list recent ingestion runs with stats.
"""

import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import WorkspaceContext, get_workspace_context
from app.models.ingestion_run import IngestionRun

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/ingestion-runs")
def list_ingestion_runs(
    limit: int = Query(default=20, ge=1, le=100),
    ctx: WorkspaceContext = Depends(get_workspace_context),
):
    """List recent ingestion runs for observability."""
    db = ctx.db
    runs = db.scalars(
        select(IngestionRun)
        .where(IngestionRun.workspace_id == ctx.workspace_id)
        .order_by(IngestionRun.started_at.desc())
        .limit(limit)
    ).all()

    return {
        "data": [
            {
                "id": str(r.id),
                "feedType": r.feed_type,
                "status": r.status,
                "startedAt": r.started_at.isoformat(),
                "completedAt": r.completed_at.isoformat() if r.completed_at else None,
                "itemsFetched": r.items_fetched,
                "itemsDeduped": r.items_deduped,
                "accountsCreated": r.accounts_created,
                "accountsExisting": r.accounts_existing,
                "rawEventsCreated": r.raw_events_created,
                "signalsCreated": r.signals_created,
                "signalsSkipped": r.signals_skipped,
                "errors": r.errors,
                "errorDetail": r.error_detail,
                "skipReasons": r.skip_reasons,
            }
            for r in runs
        ]
    }
