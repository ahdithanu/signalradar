"""Crunchbase funding round extractor.

Calls the Crunchbase Basic API to retrieve funding rounds for a given
organization.  Requires CRUNCHBASE_API_KEY to be set.

API docs: https://data.crunchbase.com/docs/using-the-api
Endpoint: GET /api/v4/entities/organizations/{slug}/cards/raised_funding_rounds
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx

from app.config import settings
from app.models.account_source import AccountSource
from app.ingestion.extractors.base import BaseExtractor, ExtractedEvent

logger = logging.getLogger(__name__)

CRUNCHBASE_BASE = "https://api.crunchbase.com/api/v4"
REQUEST_TIMEOUT = 15.0


class CrunchbaseExtractor:
    """Extracts funding round events from the Crunchbase API."""

    def extract(self, source: AccountSource) -> list[ExtractedEvent]:
        api_key = settings.crunchbase_api_key
        if not api_key:
            logger.warning(
                "CRUNCHBASE_API_KEY not set — skipping source %s", source.id
            )
            return []

        slug = source.source_key
        if not slug:
            logger.warning(
                "No source_key (crunchbase slug) for source %s — skipping",
                source.id,
            )
            return []

        url = (
            f"{CRUNCHBASE_BASE}/entities/organizations/{slug}"
            f"/cards/raised_funding_rounds"
        )

        try:
            resp = httpx.get(
                url,
                headers={"X-cb-user-key": api_key},
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Crunchbase API %s for %s: %s",
                exc.response.status_code,
                slug,
                exc.response.text[:200],
            )
            return []
        except httpx.RequestError as exc:
            logger.error("Crunchbase request failed for %s: %s", slug, exc)
            return []

        data = resp.json()
        cards = data.get("cards", {}).get("raised_funding_rounds", [])

        events: list[ExtractedEvent] = []
        for round_data in cards:
            props = round_data.get("properties", {})
            identifier = round_data.get("identifier", {})

            round_uuid = identifier.get("uuid") or props.get("identifier", {}).get("uuid")
            money_raised = props.get("money_raised", {})
            announced_on = props.get("announced_on")
            investment_type = props.get("investment_type") or "Unknown Round"

            # Parse amount
            amount_usd = money_raised.get("value_usd") if money_raised else None

            # Parse investors
            lead_investors = []
            for inv in props.get("lead_investor_identifiers", []):
                inv_name = inv.get("value")
                if inv_name:
                    lead_investors.append(inv_name)

            # Parse date
            occurred = None
            if announced_on:
                try:
                    occurred = datetime.strptime(announced_on, "%Y-%m-%d").replace(
                        tzinfo=timezone.utc
                    )
                except ValueError:
                    pass

            payload = {
                "round_type": investment_type,
                "money_raised_usd": amount_usd,
                "announced_on": announced_on,
                "lead_investors": lead_investors,
                "crunchbase_round_uuid": round_uuid,
                "source": "crunchbase",
            }

            external_id = f"cb:{round_uuid}" if round_uuid else None

            events.append(
                ExtractedEvent(
                    account_source_id=source.id,
                    account_id=source.account_id,
                    event_type="funding_round",
                    raw_payload=payload,
                    source_url=url,
                    external_id=external_id,
                    occurred_at=occurred,
                )
            )

        logger.info(
            "Crunchbase extracted %d funding rounds for %s", len(events), slug
        )
        return events
