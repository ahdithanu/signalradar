"""FMP M&A feed extractor — real implementation.

Calls FMP /mergers-acquisitions-rss-feed and returns FeedItems.
Requires FMP_API_KEY in config.

To swap from simulated to real: set FMP_API_KEY in your .env
and use FmpMaExtractor instead of SimulatedFmpMaExtractor in daily_feed.py.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx

from app.config import settings
from app.ingestion.extractors.feed_base import FeedItem

logger = logging.getLogger(__name__)


class FmpMaExtractor:
    """Real FMP M&A feed extractor."""

    def extract(self) -> list[FeedItem]:
        if not settings.fmp_api_key:
            logger.error("FMP_API_KEY not set — cannot fetch M&A feed")
            return []

        url = f"{settings.fmp_base_url}/mergers-acquisitions-rss-feed"
        params = {"page": 0, "apikey": settings.fmp_api_key}

        try:
            resp = httpx.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as e:
            logger.error("FMP M&A API returned %d: %s", e.response.status_code, str(e)[:200])
            return []
        except Exception as e:
            logger.error("FMP M&A API request failed: %s", str(e)[:200])
            return []

        if not isinstance(data, list):
            logger.warning("FMP M&A response is not a list: %s", type(data))
            return []

        items: list[FeedItem] = []
        seen_ids: set[str] = set()

        for record in data:
            symbol = record.get("symbol", "")
            target_symbol = record.get("targetedSymbol", "")
            company_name = record.get("companyName", "")
            target_name = record.get("targetedCompanyName", "")
            tx_date = record.get("transactionDate", "")

            # Skip warrants and duplicate symbol variants
            if symbol.endswith("-WT") or symbol.endswith("-WT "):
                continue

            # Parse date
            try:
                occurred_at = datetime.strptime(tx_date, "%Y-%m-%d").replace(
                    tzinfo=timezone.utc
                )
            except (ValueError, TypeError):
                occurred_at = datetime.now(timezone.utc)

            # Acquirer event
            acq_id = f"fmp_ma_acq_{symbol}_{target_symbol}_{tx_date}"
            if acq_id not in seen_ids and company_name:
                seen_ids.add(acq_id)
                items.append(FeedItem(
                    external_id=acq_id,
                    ticker=symbol if symbol else None,
                    company_name=company_name,
                    event_type="ma_activity",
                    raw_payload={
                        "role": "acquirer",
                        "symbol": symbol,
                        "companyName": company_name,
                        "targetedSymbol": target_symbol,
                        "targetedCompanyName": target_name,
                        "transactionDate": tx_date,
                        "link": record.get("link", ""),
                        "cik": record.get("cik", ""),
                    },
                    source_url=record.get("link"),
                    occurred_at=occurred_at,
                ))

            # Target event
            tgt_id = f"fmp_ma_tgt_{target_symbol}_{symbol}_{tx_date}"
            if tgt_id not in seen_ids and target_name:
                seen_ids.add(tgt_id)
                items.append(FeedItem(
                    external_id=tgt_id,
                    ticker=target_symbol if target_symbol else None,
                    company_name=target_name,
                    event_type="ma_activity",
                    raw_payload={
                        "role": "target",
                        "symbol": target_symbol,
                        "companyName": target_name,
                        "acquirerSymbol": symbol,
                        "acquirerCompanyName": company_name,
                        "transactionDate": tx_date,
                        "link": record.get("link", ""),
                        "cik": record.get("targetedCik", ""),
                    },
                    source_url=record.get("link"),
                    occurred_at=occurred_at,
                ))

        logger.info("FMP M&A extractor: fetched %d items from %d records", len(items), len(data))
        return items
