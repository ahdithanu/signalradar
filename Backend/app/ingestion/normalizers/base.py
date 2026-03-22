"""Base protocol for all normalizers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.models.raw_event import RawEvent


class SkipEvent(Exception):
    """Raised by a normalizer when a raw event should be skipped.

    The message becomes the status_detail on the raw_event row,
    giving pipeline operators a clear reason why the event was not
    converted to a signal.
    """


@dataclass
class NormalizedSignal:
    """Data transfer object returned by a normalizer.

    Represents a product-layer signal ready to be inserted into the signals
    table.  Does NOT include score — scoring is derived at query time.
    """

    signal_type: str
    title: str
    summary: str | None
    occurred_at: datetime


class BaseNormalizer(Protocol):
    """Interface every normalizer must implement."""

    def normalize(self, event: RawEvent) -> NormalizedSignal | None:
        """Transform a raw event into a product signal.

        Returns None if the event does not qualify as a signal.
        Raise SkipEvent with a descriptive message to mark the event
        as skipped with a clear status_detail.
        Must not write to the database.
        """
        ...
