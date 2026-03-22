"""Base protocol for all extractors."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from app.models.account_source import AccountSource


@dataclass
class ExtractedEvent:
    """Data transfer object returned by an extractor.

    Represents a single raw event before it is persisted to raw_events.
    """

    account_source_id: uuid.UUID
    account_id: uuid.UUID
    event_type: str
    raw_payload: dict
    source_url: str | None = None
    external_id: str | None = None
    occurred_at: datetime | None = None


class BaseExtractor(Protocol):
    """Interface every extractor must implement."""

    def extract(self, source: AccountSource) -> list[ExtractedEvent]:
        """Fetch data from an external source and return raw events.

        Must not write to the database.
        Must not raise on transient errors — return empty list instead.
        Must populate external_id where possible for dedup.
        """
        ...
