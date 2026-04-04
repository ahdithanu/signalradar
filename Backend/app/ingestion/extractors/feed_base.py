"""Base interface for global feed extractors.

Unlike account-source extractors (which pull data for a specific account),
feed extractors pull a global batch of events and return them with enough
metadata to resolve accounts later.

All feed extractors must implement this interface.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass
class FeedItem:
    """Single item from a global feed.

    Contains enough info to:
    1. Resolve or create an Account (via ticker/name/domain)
    2. Create a RawEvent
    3. Normalize into a Signal
    """

    # Identity — used for dedup
    external_id: str

    # Account resolution fields
    ticker: str | None
    company_name: str
    domain: str | None = None

    # Event data
    event_type: str = "ma_activity"
    raw_payload: dict | None = None
    source_url: str | None = None
    occurred_at: datetime | None = None


class BaseFeedExtractor(Protocol):
    """Interface every feed extractor must implement."""

    def extract(self) -> list[FeedItem]:
        """Fetch a batch of events from a global feed.

        Returns a list of FeedItems. Does not write to the database.
        Must populate external_id for dedup.
        Must handle transient errors gracefully (return empty list).
        """
        ...
