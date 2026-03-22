"""M&A activity normalizer — converts raw M&A events into funding signals.

An M&A event is a high-confidence funding signal because:
- Acquirers are deploying capital (buying signal for vendor consolidation)
- Targets are receiving capital and will restructure (buying signal for new tools)

Both sides of a deal are actionable for outbound.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta

from app.ingestion.normalizers.base import NormalizedSignal, SkipEvent
from app.models.raw_event import RawEvent

logger = logging.getLogger(__name__)

# Skip events older than this
MAX_AGE_DAYS = 90


class MaFundingNormalizer:
    """Normalize M&A raw events into funding signals."""

    def normalize(self, event: RawEvent) -> NormalizedSignal | None:
        payload = event.raw_payload or {}
        role = payload.get("role", "unknown")
        tx_date_str = payload.get("transactionDate", "")

        # Parse transaction date
        try:
            occurred_at = datetime.strptime(tx_date_str, "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
        except (ValueError, TypeError):
            occurred_at = event.occurred_at or datetime.now(timezone.utc)

        # Skip stale events
        age = (datetime.now(timezone.utc) - occurred_at).days
        if age > MAX_AGE_DAYS:
            raise SkipEvent(f"Event is {age} days old (max {MAX_AGE_DAYS})")

        if role == "acquirer":
            target_name = payload.get("targetedCompanyName", "unknown company")
            target_symbol = payload.get("targetedSymbol", "")
            target_label = f"{target_name} ({target_symbol})" if target_symbol else target_name

            title = f"Acquiring {target_label}"
            summary = (
                f"SEC filing dated {tx_date_str}. "
                f"{payload.get('companyName', 'Company')} is acquiring {target_label}. "
                f"M&A activity signals capital deployment, potential vendor consolidation, "
                f"and organizational restructuring."
            )

        elif role == "target":
            acquirer_name = payload.get("acquirerCompanyName", "unknown company")
            acquirer_symbol = payload.get("acquirerSymbol", "")
            acquirer_label = f"{acquirer_name} ({acquirer_symbol})" if acquirer_symbol else acquirer_name

            title = f"Being acquired by {acquirer_label}"
            summary = (
                f"SEC filing dated {tx_date_str}. "
                f"{payload.get('companyName', 'Company')} is being acquired by {acquirer_label}. "
                f"Acquisition targets typically restructure tooling and vendor relationships "
                f"during integration."
            )

        else:
            raise SkipEvent(f"Unknown M&A role: {role}")

        return NormalizedSignal(
            signal_type="funding",
            title=title,
            summary=summary,
            occurred_at=occurred_at,
        )
