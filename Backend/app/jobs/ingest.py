"""CLI entry point for the ingestion pipeline.

Usage:
    python -m app.jobs.ingest --type funding
    python -m app.jobs.ingest --type funding --simulate
    python -m app.jobs.ingest --type funding --dry-run
    python -m app.jobs.ingest --type funding --simulate --dry-run
    python -m app.jobs.ingest --type funding --account-id UUID
    python -m app.jobs.ingest --type funding --limit 10
    python -m app.jobs.ingest --normalize-only
    python -m app.jobs.ingest --normalize-only --event-type funding_round
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import uuid

# Ensure all models are imported so create_all sees them
from app.models import Account, Signal, AccountSource, RawEvent  # noqa: F401
from app.db import SessionLocal
from app.ingestion.runner import (
    register_extractor,
    register_normalizer,
    run_extraction,
    run_normalization,
    run_pipeline,
)
from app.ingestion.extractors.crunchbase import CrunchbaseExtractor
from app.ingestion.extractors.simulated import SimulatedCrunchbaseExtractor
from app.ingestion.extractors.simulated_website import SimulatedWebsiteExtractor
from app.ingestion.normalizers.funding import FundingNormalizer
from app.ingestion.normalizers.positioning import PositioningNormalizer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Map: pipeline type → (source_type, event_type)
PIPELINE_MAP = {
    "funding": ("crunchbase", "funding_round"),
    "positioning": ("website", "website_change"),
}


def _register_all(simulate: bool = False) -> None:
    """Register all extractors and normalizers."""
    if simulate:
        register_extractor("crunchbase", SimulatedCrunchbaseExtractor())
        register_extractor("website", SimulatedWebsiteExtractor())
        logger.info("Using SIMULATED extractors (no API calls)")
    else:
        register_extractor("crunchbase", CrunchbaseExtractor())
        # No real website extractor yet — only simulated
        register_extractor("website", SimulatedWebsiteExtractor())
    register_normalizer("funding_round", FundingNormalizer())
    register_normalizer("website_change", PositioningNormalizer())


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Signal Radar ingestion pipeline"
    )
    parser.add_argument(
        "--type",
        choices=list(PIPELINE_MAP.keys()),
        help="Signal type to extract and normalize",
    )
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Use simulated data instead of real API calls (for local testing)",
    )
    parser.add_argument(
        "--normalize-only",
        action="store_true",
        help="Skip extraction, only normalize pending raw events",
    )
    parser.add_argument(
        "--event-type",
        help="Filter normalization to a specific event_type (e.g., funding_round)",
    )
    parser.add_argument(
        "--account-id",
        type=uuid.UUID,
        help="Run for a single account",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Process at most N account sources",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log what would be created without writing to DB",
    )

    args = parser.parse_args()

    if not args.type and not args.normalize_only:
        parser.error("Must specify --type or --normalize-only")

    _register_all(simulate=args.simulate)

    db = SessionLocal()
    try:
        if args.normalize_only:
            logger.info("Running normalization only (event_type=%s)", args.event_type)
            stats = run_normalization(
                db,
                event_type=args.event_type,
                dry_run=args.dry_run,
            )
        else:
            source_type, event_type = PIPELINE_MAP[args.type]
            logger.info(
                "Running pipeline: type=%s source=%s event=%s simulate=%s account=%s limit=%s dry_run=%s",
                args.type,
                source_type,
                event_type,
                args.simulate,
                args.account_id,
                args.limit,
                args.dry_run,
            )
            stats = run_pipeline(
                db,
                source_type=source_type,
                event_type=event_type,
                account_id=args.account_id,
                limit=args.limit,
                dry_run=args.dry_run,
            )

        print(json.dumps(stats, indent=2))

    except Exception:
        logger.exception("Ingestion pipeline failed")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
