"""Daily feed ingestion CLI.

Runs the funding feed pipeline end-to-end:
  1. Extract M&A events (simulated or real FMP)
  2. Resolve or create accounts
  3. Create raw events
  4. Normalize into signals
  5. Record observability stats

Usage:
    python -m app.jobs.daily_feed                     # run with simulated data
    python -m app.jobs.daily_feed --real               # run with real FMP API
    python -m app.jobs.daily_feed --dry-run             # preview without DB writes
    python -m app.jobs.daily_feed --real --dry-run      # preview real FMP data

The --real flag requires FMP_API_KEY to be set in the environment.
Without --real, the simulated extractor is used (same pipeline, fake data).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import uuid

from app.config import settings
from app.db import SessionLocal
from app.models import (  # noqa: F401 — ensure all models loaded
    Account, Signal, RawEvent, IngestionRun,
    User, Workspace, WorkspaceMember, AccountSource,
)
from app.ingestion.feed_runner import run_feed
from app.ingestion.normalizers.ma_funding import MaFundingNormalizer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# System workspace for the shared daily feed.
# All feed-discovered accounts and signals belong to this workspace.
SYSTEM_WORKSPACE_ID = uuid.UUID("cccccccc-0000-0000-0000-000000000001")
SYSTEM_WORKSPACE_NAME = "Signal Radar Feed"


def _ensure_system_workspace(db) -> None:
    """Create the system workspace if it doesn't exist."""
    from app.models.workspace import Workspace
    from app.models.user import User
    from app.auth import DEFAULT_USER_ID

    ws = db.get(Workspace, SYSTEM_WORKSPACE_ID)
    if ws is None:
        # Ensure the system user exists first
        user = db.get(User, DEFAULT_USER_ID)
        if user is None:
            user = User(
                id=DEFAULT_USER_ID,
                email="system@signalradar.local",
                display_name="System",
            )
            db.add(user)
            db.flush()

        ws = Workspace(
            id=SYSTEM_WORKSPACE_ID,
            name=SYSTEM_WORKSPACE_NAME,
            created_by=DEFAULT_USER_ID,
        )
        db.add(ws)

        # Add default user as owner
        from app.models.workspace import WorkspaceMember
        db.add(WorkspaceMember(
            user_id=DEFAULT_USER_ID,
            workspace_id=SYSTEM_WORKSPACE_ID,
            role="owner",
        ))
        db.commit()
        logger.info("Created system workspace: %s", SYSTEM_WORKSPACE_ID)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Signal Radar daily feed ingestion"
    )
    parser.add_argument(
        "--real",
        action="store_true",
        help="Use real FMP API instead of simulated data (requires FMP_API_KEY)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log what would be created without writing to DB",
    )

    args = parser.parse_args()

    # Select extractor
    if args.real:
        if not settings.fmp_api_key:
            logger.error("--real requires FMP_API_KEY to be set. Exiting.")
            sys.exit(1)
        from app.ingestion.extractors.fmp_ma import FmpMaExtractor
        extractor = FmpMaExtractor()
        logger.info("Using REAL FMP M&A extractor")
    else:
        from app.ingestion.extractors.simulated_fmp_ma import SimulatedFmpMaExtractor
        extractor = SimulatedFmpMaExtractor()
        logger.info("Using SIMULATED FMP M&A extractor")

    normalizer = MaFundingNormalizer()

    db = SessionLocal()
    try:
        _ensure_system_workspace(db)

        stats = run_feed(
            db=db,
            workspace_id=SYSTEM_WORKSPACE_ID,
            extractor=extractor,
            normalizer=normalizer,
            feed_type="funding_ma",
            dry_run=args.dry_run,
        )

        print(json.dumps(stats, indent=2, default=str))

    except Exception:
        logger.exception("Daily feed pipeline failed")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
