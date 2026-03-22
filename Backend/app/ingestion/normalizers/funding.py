"""Funding round normalizer.

Transforms raw funding_round events (from Crunchbase or similar) into
product-layer signals of type "funding".

Hardened against real-world data issues:
- missing round_type → "Unknown Round"
- missing money_raised_usd → "undisclosed amount"
- missing occurred_at → falls back to fetched_at
- completely empty payload → SkipEvent with reason
- non-numeric amount → treated as None (undisclosed)
- negative amount → treated as None (undisclosed)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.models.raw_event import RawEvent
from app.ingestion.normalizers.base import NormalizedSignal, SkipEvent

logger = logging.getLogger(__name__)


def _format_amount(amount_usd: float | int | None) -> str:
    """Format a dollar amount for display.

    Returns 'undisclosed amount' for None, non-numeric, zero, or negative values.
    """
    if amount_usd is None:
        return "undisclosed amount"
    # Guard against non-numeric values that slipped past extraction
    try:
        amount_usd = float(amount_usd)
    except (TypeError, ValueError):
        return "undisclosed amount"
    if amount_usd <= 0:
        return "undisclosed amount"
    if amount_usd >= 1_000_000_000:
        return f"${amount_usd / 1_000_000_000:.1f}B"
    if amount_usd >= 1_000_000:
        return f"${amount_usd / 1_000_000:.0f}M"
    if amount_usd >= 1_000:
        return f"${amount_usd / 1_000:.0f}K"
    return f"${amount_usd:.0f}"


def _interpret_round(round_type: str | None) -> str:
    """Rules-based summary from round type.

    Handles None and unknown types gracefully.
    """
    if not round_type:
        return "New funding may signal expansion and hiring."
    round_lower = round_type.lower()
    if "seed" in round_lower or "pre_seed" in round_lower:
        return "Early-stage company beginning to build GTM function."
    if "series_a" in round_lower or "series a" in round_lower:
        return "Entering rapid scaling phase and likely expanding GTM team."
    if "series_b" in round_lower or "series b" in round_lower:
        return "Growth-stage company likely optimizing revenue operations."
    if "series_c" in round_lower:
        return "Late-stage company likely expanding into new markets or segments."
    if "debt" in round_lower or "grant" in round_lower:
        return "Non-dilutive funding may signal cautious expansion."
    return "New funding may signal expansion and hiring."


def _is_empty_payload(payload: dict) -> bool:
    """Return True if the payload has no meaningful funding data.

    Checks only signal-relevant fields: round_type, money_raised_usd,
    announced_on, lead_investors. Metadata fields like 'source' and
    'crunchbase_round_uuid' are ignored — they don't carry signal value.
    """
    SIGNAL_FIELDS = ("round_type", "money_raised_usd", "announced_on", "lead_investors")
    for key in SIGNAL_FIELDS:
        value = payload.get(key)
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        if isinstance(value, list) and len(value) == 0:
            continue
        return False
    return True


class FundingNormalizer:
    """Normalizes funding_round raw events into funding signals.

    Raises SkipEvent for events that should not become signals.
    Returns NormalizedSignal for valid events with safe fallbacks
    for missing fields.
    """

    def normalize(self, event: RawEvent) -> NormalizedSignal | None:
        if event.event_type != "funding_round":
            return None

        payload = event.raw_payload
        if not isinstance(payload, dict):
            raise SkipEvent(
                f"Invalid payload type: {type(payload).__name__} (expected dict)"
            )

        # Reject completely empty payloads — no signal value
        if _is_empty_payload(payload):
            raise SkipEvent(
                "Empty funding payload — no round type, amount, or date"
            )

        round_type = payload.get("round_type")  # may be None
        amount_usd = payload.get("money_raised_usd")
        announced_on = payload.get("announced_on")
        lead_investors = payload.get("lead_investors")

        # Sanitize lead_investors
        if not isinstance(lead_investors, list):
            lead_investors = []
        # Filter out None/empty entries
        lead_investors = [inv for inv in lead_investors if inv and isinstance(inv, str)]

        # Build title with safe fallbacks
        amount_str = _format_amount(amount_usd)
        if round_type:
            display_round = round_type.replace("_", " ").title()
            title = f"Raised {amount_str} {display_round}"
        else:
            title = f"Raised {amount_str} funding round"

        # Build summary
        base_summary = _interpret_round(round_type)
        if lead_investors:
            investors_str = ", ".join(lead_investors[:3])
            summary = f"Led by {investors_str}. {base_summary}"
        else:
            summary = base_summary

        # Determine occurred_at — 3 fallback levels:
        # 1. event.occurred_at (set by extractor from parsed date)
        # 2. announced_on string in payload (re-parse as safety net)
        # 3. event.fetched_at (always present)
        occurred_at = event.occurred_at
        if occurred_at is None and announced_on and isinstance(announced_on, str):
            try:
                occurred_at = datetime.strptime(announced_on, "%Y-%m-%d").replace(
                    tzinfo=timezone.utc
                )
            except ValueError:
                logger.debug(
                    "Malformed date '%s' in raw_event %s — falling back to fetched_at",
                    announced_on,
                    event.id,
                )
        if occurred_at is None:
            occurred_at = event.fetched_at
            logger.debug(
                "No occurred_at for raw_event %s — using fetched_at %s",
                event.id,
                occurred_at,
            )

        return NormalizedSignal(
            signal_type="funding",
            title=title,
            summary=summary,
            occurred_at=occurred_at,
        )
