import uuid
import hashlib
import json
from datetime import datetime, timezone

from sqlalchemy import String, Text, DateTime, ForeignKey, Index, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RawEvent(Base):
    __tablename__ = "raw_events"
    __table_args__ = (
        Index("ix_raw_events_account_type_fetched", "account_id", "event_type", "fetched_at"),
        Index("ix_raw_events_status_type", "status", "event_type"),
        Index("ix_raw_events_workspace", "workspace_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    account_source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("account_sources.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    raw_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, unique=True, index=True
    )
    content_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    occurred_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )
    status_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    account_source: Mapped["AccountSource"] = relationship(
        "AccountSource", back_populates="raw_events"
    )
    account: Mapped["Account"] = relationship("Account")

    @staticmethod
    def compute_content_hash(
        account_id: uuid.UUID, event_type: str, payload: dict
    ) -> str:
        """Deterministic hash for dedup when no external_id exists."""
        canonical = json.dumps(payload, sort_keys=True, default=str)
        raw = f"{account_id}:{event_type}:{canonical}"
        return hashlib.sha256(raw.encode()).hexdigest()


from app.models.account import Account  # noqa: E402, F401
from app.models.account_source import AccountSource  # noqa: E402, F401
