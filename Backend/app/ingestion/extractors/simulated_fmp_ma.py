"""Simulated FMP M&A feed extractor.

Returns realistic M&A events in the exact same FeedItem shape as the real
FmpMaExtractor. Used for:
1. Local development without FMP API key
2. End-to-end pipeline testing
3. Demo data generation

The simulated dataset contains 15 realistic M&A events across different
industries, company sizes, and transaction types.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta

from app.ingestion.extractors.feed_base import FeedItem

logger = logging.getLogger(__name__)


def _days_ago(days: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days)


# 15 simulated M&A records matching the exact FMP response shape.
# Each generates 2 FeedItems (acquirer + target) = 30 total items.
SIMULATED_MA_RECORDS = [
    {
        "symbol": "IONQ",
        "companyName": "IonQ, Inc.",
        "cik": "0001824920",
        "targetedCompanyName": "SkyWater Technology, Inc.",
        "targetedCik": "0001819974",
        "targetedSymbol": "SKYT",
        "transactionDate": _days_ago(2).strftime("%Y-%m-%d"),
        "link": "https://www.sec.gov/Archives/edgar/data/1824920/000119312526117933/d88629ds4.htm",
    },
    {
        "symbol": "PLTR",
        "companyName": "Palantir Technologies Inc.",
        "cik": "0001321655",
        "targetedCompanyName": "Decisive Analytics Corporation",
        "targetedCik": "0001532802",
        "targetedSymbol": "DACS",
        "transactionDate": _days_ago(5).strftime("%Y-%m-%d"),
        "link": "https://www.sec.gov/Archives/edgar/data/1321655/000119312526118000/example.htm",
    },
    {
        "symbol": "CRM",
        "companyName": "Salesforce, Inc.",
        "cik": "0001108524",
        "targetedCompanyName": "Informatica Inc.",
        "targetedCik": "0001047880",
        "targetedSymbol": "INFA",
        "transactionDate": _days_ago(8).strftime("%Y-%m-%d"),
        "link": "https://www.sec.gov/Archives/edgar/data/1108524/000119312526118001/example.htm",
    },
    {
        "symbol": "GOOGL",
        "companyName": "Alphabet Inc.",
        "cik": "0001652044",
        "targetedCompanyName": "Wiz, Inc.",
        "targetedCik": "0001900123",
        "targetedSymbol": "",
        "transactionDate": _days_ago(12).strftime("%Y-%m-%d"),
        "link": "https://www.sec.gov/Archives/edgar/data/1652044/000119312526118002/example.htm",
    },
    {
        "symbol": "AMZN",
        "companyName": "Amazon.com, Inc.",
        "cik": "0001018724",
        "targetedCompanyName": "Anthropic, Inc.",
        "targetedCik": "0001950001",
        "targetedSymbol": "",
        "transactionDate": _days_ago(15).strftime("%Y-%m-%d"),
        "link": "https://www.sec.gov/Archives/edgar/data/1018724/000119312526118003/example.htm",
    },
    {
        "symbol": "MSFT",
        "companyName": "Microsoft Corporation",
        "cik": "0000789019",
        "targetedCompanyName": "Nuance Communications, Inc.",
        "targetedCik": "0001022793",
        "targetedSymbol": "NUAN",
        "transactionDate": _days_ago(18).strftime("%Y-%m-%d"),
        "link": "https://www.sec.gov/Archives/edgar/data/789019/000119312526118004/example.htm",
    },
    {
        "symbol": "SNOW",
        "companyName": "Snowflake Inc.",
        "cik": "0001640147",
        "targetedCompanyName": "Neeva, Inc.",
        "targetedCik": "0001880001",
        "targetedSymbol": "",
        "transactionDate": _days_ago(22).strftime("%Y-%m-%d"),
        "link": "https://www.sec.gov/Archives/edgar/data/1640147/000119312526118005/example.htm",
    },
    {
        "symbol": "PANW",
        "companyName": "Palo Alto Networks, Inc.",
        "cik": "0001327567",
        "targetedCompanyName": "Talon Cyber Security Ltd.",
        "targetedCik": "0001920001",
        "targetedSymbol": "",
        "transactionDate": _days_ago(25).strftime("%Y-%m-%d"),
        "link": "https://www.sec.gov/Archives/edgar/data/1327567/000119312526118006/example.htm",
    },
    {
        "symbol": "ZS",
        "companyName": "Zscaler, Inc.",
        "cik": "0001713683",
        "targetedCompanyName": "ShiftRight, Inc.",
        "targetedCik": "0001930001",
        "targetedSymbol": "",
        "transactionDate": _days_ago(3).strftime("%Y-%m-%d"),
        "link": "https://www.sec.gov/Archives/edgar/data/1713683/000119312526118007/example.htm",
    },
    {
        "symbol": "DDOG",
        "companyName": "Datadog, Inc.",
        "cik": "0001561550",
        "targetedCompanyName": "Sqreen SAS",
        "targetedCik": "0001910001",
        "targetedSymbol": "",
        "transactionDate": _days_ago(30).strftime("%Y-%m-%d"),
        "link": "https://www.sec.gov/Archives/edgar/data/1561550/000119312526118008/example.htm",
    },
    {
        "symbol": "HUBS",
        "companyName": "HubSpot, Inc.",
        "cik": "0001404655",
        "targetedCompanyName": "Clearbit, Inc.",
        "targetedCik": "0001915001",
        "targetedSymbol": "",
        "transactionDate": _days_ago(7).strftime("%Y-%m-%d"),
        "link": "https://www.sec.gov/Archives/edgar/data/1404655/000119312526118009/example.htm",
    },
    {
        "symbol": "CRWD",
        "companyName": "CrowdStrike Holdings, Inc.",
        "cik": "0001535527",
        "targetedCompanyName": "Bionic.ai Ltd.",
        "targetedCik": "0001925001",
        "targetedSymbol": "",
        "transactionDate": _days_ago(10).strftime("%Y-%m-%d"),
        "link": "https://www.sec.gov/Archives/edgar/data/1535527/000119312526118010/example.htm",
    },
    {
        "symbol": "BILL",
        "companyName": "BILL Holdings, Inc.",
        "cik": "0001786352",
        "targetedCompanyName": "Finmark Financial, Inc.",
        "targetedCik": "0001935001",
        "targetedSymbol": "",
        "transactionDate": _days_ago(14).strftime("%Y-%m-%d"),
        "link": "https://www.sec.gov/Archives/edgar/data/1786352/000119312526118011/example.htm",
    },
    {
        "symbol": "TWLO",
        "companyName": "Twilio Inc.",
        "cik": "0001447669",
        "targetedCompanyName": "Segment.io, Inc.",
        "targetedCik": "0001940001",
        "targetedSymbol": "",
        "transactionDate": _days_ago(35).strftime("%Y-%m-%d"),
        "link": "https://www.sec.gov/Archives/edgar/data/1447669/000119312526118012/example.htm",
    },
    {
        "symbol": "NET",
        "companyName": "Cloudflare, Inc.",
        "cik": "0001477333",
        "targetedCompanyName": "Area 1 Security, Inc.",
        "targetedCik": "0001945001",
        "targetedSymbol": "",
        "transactionDate": _days_ago(40).strftime("%Y-%m-%d"),
        "link": "https://www.sec.gov/Archives/edgar/data/1477333/000119312526118013/example.htm",
    },
]


class SimulatedFmpMaExtractor:
    """Simulated FMP M&A feed extractor.

    Returns realistic M&A events without making any API calls.
    Same output shape as FmpMaExtractor — pipeline is source-agnostic.
    """

    def extract(self) -> list[FeedItem]:
        items: list[FeedItem] = []
        seen_ids: set[str] = set()

        for record in SIMULATED_MA_RECORDS:
            symbol = record["symbol"]
            target_symbol = record.get("targetedSymbol", "")
            company_name = record["companyName"]
            target_name = record["targetedCompanyName"]
            tx_date = record["transactionDate"]

            # Skip warrants
            if symbol.endswith("-WT"):
                continue

            try:
                occurred_at = datetime.strptime(tx_date, "%Y-%m-%d").replace(
                    tzinfo=timezone.utc
                )
            except (ValueError, TypeError):
                occurred_at = datetime.now(timezone.utc)

            # Acquirer event
            acq_id = f"fmp_ma_acq_{symbol}_{target_symbol}_{tx_date}"
            if acq_id not in seen_ids:
                seen_ids.add(acq_id)
                items.append(FeedItem(
                    external_id=acq_id,
                    ticker=symbol,
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

            # Target event (only if target has a name)
            if target_name:
                tgt_id = f"fmp_ma_tgt_{target_symbol or 'private'}_{symbol}_{tx_date}"
                if tgt_id not in seen_ids:
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

        logger.info(
            "Simulated FMP M&A extractor: produced %d items from %d records",
            len(items),
            len(SIMULATED_MA_RECORDS),
        )
        return items
