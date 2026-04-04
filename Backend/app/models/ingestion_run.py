"""IngestionRun — observability record for every feed ingestion execution.

One row per run. Tracks counters for fetched, deduped, created, skipped items.
Queryable via GET /admin/ingestion-runs.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Integer, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    feed_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Counters
    items_fetched: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    items_deduped: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    accounts_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    accounts_existing: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    raw_events_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    signals_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    signals_skipped: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    errors: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Details
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    skip_reasons: Mapped[dict | None] = mapped_column(JSON, nullable=True)
