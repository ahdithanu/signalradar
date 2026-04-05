"""Simulated funding extractor for local testing.

Produces realistic funding round events for the 8 seed accounts without
calling any external API.  Used when CRUNCHBASE_API_KEY is not available
or when --simulate is passed to the CLI.

Includes intentional edge-case events to verify normalizer robustness:
- missing round_type
- missing money_raised_usd
- duplicate external_id across two events
- same payload with different external_id (content_hash dedup test)
- malformed announced_on date
- completely empty payload
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone, timedelta

from app.models.account_source import AccountSource
from app.ingestion.extractors.base import ExtractedEvent

logger = logging.getLogger(__name__)


# Simulated Crunchbase-like funding rounds per source_key.
# Accounts 1,2,5,8 already have seed funding signals.
# Accounts 3,4,6,7 do NOT have seed funding signals — these are net-new.
#
# Edge-case events are marked with comments.
_SIMULATED_ROUNDS: dict[str, list[dict]] = {
    "nova-payments": [
        {
            "round_uuid": "sim-cb-round-nova-001",
            "round_type": "series_a",
            "money_raised_usd": 18_000_000,
            "announced_on": "2026-01-28",
            "lead_investors": ["Index Ventures"],
        },
        # EDGE CASE: missing round_type (None)
        {
            "round_uuid": "sim-cb-round-nova-002",
            "round_type": None,
            "money_raised_usd": 3_000_000,
            "announced_on": "2025-06-15",
            "lead_investors": ["Angel Syndicate"],
        },
    ],
    "ramp-ai": [
        {
            "round_uuid": "sim-cb-round-ramp-001",
            "round_type": "series_a",
            "money_raised_usd": 12_000_000,
            "announced_on": "2026-02-01",
            "lead_investors": ["a16z"],
        },
        # EDGE CASE: missing money_raised_usd (None)
        {
            "round_uuid": "sim-cb-round-ramp-002",
            "round_type": "seed",
            "money_raised_usd": None,
            "announced_on": "2025-08-10",
            "lead_investors": [],
        },
    ],
    "vector-labs": [
        {
            "round_uuid": "sim-cb-round-vector-001",
            "round_type": "series_b",
            "money_raised_usd": 35_000_000,
            "announced_on": "2026-03-10",
            "lead_investors": ["Accel", "Lightspeed Venture Partners"],
        },
        # EDGE CASE: duplicate external_id (same round_uuid as first event)
        {
            "round_uuid": "sim-cb-round-vector-001",
            "round_type": "series_b",
            "money_raised_usd": 35_000_000,
            "announced_on": "2026-03-10",
            "lead_investors": ["Accel", "Lightspeed Venture Partners"],
        },
    ],
    "cobalt-health": [
        {
            "round_uuid": "sim-cb-round-cobalt-001",
            "round_type": "series_b",
            "money_raised_usd": 28_000_000,
            "announced_on": "2026-03-05",
            "lead_investors": ["Andreessen Horowitz"],
        },
        # EDGE CASE: same payload, different external_id (tests content_hash dedup)
        {
            "round_uuid": "sim-cb-round-cobalt-002",
            "round_type": "series_b",
            "money_raised_usd": 28_000_000,
            "announced_on": "2026-03-05",
            "lead_investors": ["Andreessen Horowitz"],
        },
    ],
    "prism-analytics": [
        {
            "round_uuid": "sim-cb-round-prism-001",
            "round_type": "pre_seed",
            "money_raised_usd": 5_000_000,
            "announced_on": "2026-02-18",
            "lead_investors": ["Y Combinator"],
        },
    ],
    "meridian-logistics": [
        {
            "round_uuid": "sim-cb-round-meridian-001",
            "round_type": "series_c",
            "money_raised_usd": 60_000_000,
            "announced_on": "2026-03-12",
            "lead_investors": ["Tiger Global", "Coatue"],
        },
        # EDGE CASE: completely empty payload (no round_type, no amount, no date, no investors)
        {
            "round_uuid": "sim-cb-round-meridian-002",
            "round_type": None,
            "money_raised_usd": None,
            "announced_on": None,
            "lead_investors": None,
        },
    ],
    "athena-security": [
        {
            "round_uuid": "sim-cb-round-athena-001",
            "round_type": "series_b",
            "money_raised_usd": 22_000_000,
            "announced_on": "2026-03-01",
            "lead_investors": ["Insight Partners"],
        },
        # EDGE CASE: malformed date string
        {
            "round_uuid": "sim-cb-round-athena-002",
            "round_type": "series_a",
            "money_raised_usd": 8_000_000,
            "announced_on": "not-a-date",
            "lead_investors": ["Unknown Fund"],
        },
    ],
    "flux-commerce": [
        {
            "round_uuid": "sim-cb-round-flux-001",
            "round_type": "series_a",
            "money_raised_usd": 10_000_000,
            "announced_on": "2026-02-05",
            "lead_investors": ["General Catalyst"],
        },
    ],
}


class SimulatedCrunchbaseExtractor:
    """Returns pre-built funding events for local testing.

    Includes intentional edge-case events to exercise normalizer
    robustness and dedup logic.
    """

    def extract(self, source: AccountSource) -> list[ExtractedEvent]:
        slug = source.source_key
        if not slug:
            return []

        rounds = _SIMULATED_ROUNDS.get(slug)
        if not rounds:
            logger.info("No simulated data for slug=%s", slug)
            return []

        events: list[ExtractedEvent] = []
        for r in rounds:
            # Parse date — handle None and malformed
            occurred = None
            announced_on = r.get("announced_on")
            if announced_on:
                try:
                    occurred = datetime.strptime(
                        announced_on, "%Y-%m-%d"
                    ).replace(tzinfo=timezone.utc)
                except ValueError:
                    logger.warning(
                        "Malformed date '%s' for %s — occurred_at will be None",
                        announced_on,
                        slug,
                    )

            payload = {
                "round_type": r.get("round_type"),
                "money_raised_usd": r.get("money_raised_usd"),
                "announced_on": announced_on,
                "lead_investors": r.get("lead_investors"),
                "crunchbase_round_uuid": r.get("round_uuid"),
                "source": "simulated_crunchbase",
            }

            round_uuid = r.get("round_uuid")
            external_id = f"cb:{round_uuid}" if round_uuid else None

            events.append(
                ExtractedEvent(
                    account_source_id=source.id,
                    account_id=source.account_id,
                    event_type="funding_round",
                    raw_payload=payload,
                    source_url=f"https://www.crunchbase.com/organization/{slug}",
                    external_id=external_id,
                    occurred_at=occurred,
                )
            )

        logger.info(
            "Simulated extractor produced %d events for %s", len(events), slug
        )
        return events
