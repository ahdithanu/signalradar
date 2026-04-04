"""Feed runner — orchestrates global feed ingestion with observability.

Unlike the account-source runner (runner.py), this runner:
1. Pulls a global feed (not per-account)
2. Resolves or creates accounts from feed items
3. Creates raw events and normalizes into signals
4. Records everything in an IngestionRun for observability

Usage:
    from app.ingestion.feed_runner import run_feed
    stats = run_feed(db, workspace_id, extractor, normalizer, feed_type="funding_ma")
"""

from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.ingestion.extractors.feed_base import BaseFeedExtractor, FeedItem
from app.ingestion.normalizers.base import BaseNormalizer, NormalizedSignal, SkipEvent
from app.ingestion.account_resolver import resolve_or_create_account
from app.models.raw_event import RawEvent
from app.models.signal import Signal
from app.models.ingestion_run import IngestionRun

logger = logging.getLogger(__name__)


def _dedup_raw_event_by_external_id(db: Session, external_id: str) -> bool:
    """Return True if a raw event with this external_id already exists."""
    exists = db.scalar(
        select(RawEvent.id).where(RawEvent.external_id == external_id)
    )
    return exists is not None


def _dedup_signal(
    db: Session,
    account_id: uuid.UUID,
    signal_type: str,
    title: str,
    occurred_at: datetime,
) -> bool:
    """Return True if a similar signal already exists (same title within 7-day window)."""
    from datetime import timedelta
    window_start = occurred_at - timedelta(days=7)
    window_end = occurred_at + timedelta(days=7)
    exists = db.scalar(
        select(Signal.id).where(
            Signal.account_id == account_id,
            Signal.type == signal_type,
            Signal.title == title,
            Signal.occurred_at >= window_start,
            Signal.occurred_at <= window_end,
        )
    )
    return exists is not None


def run_feed(
    db: Session,
    workspace_id: uuid.UUID,
    extractor: BaseFeedExtractor,
    normalizer: BaseNormalizer,
    feed_type: str,
    dry_run: bool = False,
) -> dict:
    """Run a full feed ingestion cycle with observability.

    Returns the IngestionRun stats as a dict.
    """
    # Create observability record — initialize all counters explicitly
    # because SQLAlchemy column defaults only apply on flush/insert.
    run = IngestionRun(
        workspace_id=workspace_id,
        feed_type=feed_type,
        status="running",
        started_at=datetime.now(timezone.utc),
        items_fetched=0,
        items_deduped=0,
        accounts_created=0,
        accounts_existing=0,
        raw_events_created=0,
        signals_created=0,
        signals_skipped=0,
        errors=0,
    )
    if not dry_run:
        db.add(run)
        db.flush()

    skip_reasons: dict[str, int] = defaultdict(int)

    try:
        # 1. Extract
        items = extractor.extract()
        run.items_fetched = len(items)
        logger.info("[%s] Fetched %d items", feed_type, len(items))

        # Track external_ids seen this batch
        seen_external_ids: set[str] = set()

        for item in items:
            try:
                _process_feed_item(
                    db=db,
                    workspace_id=workspace_id,
                    item=item,
                    normalizer=normalizer,
                    run=run,
                    skip_reasons=skip_reasons,
                    seen_external_ids=seen_external_ids,
                    dry_run=dry_run,
                )
            except Exception as exc:
                logger.error(
                    "[%s] Error processing item %s: %s",
                    feed_type, item.external_id, str(exc)[:200],
                )
                run.errors += 1
                skip_reasons["processing_error"] += 1

        run.status = "completed"

    except Exception as exc:
        logger.exception("[%s] Feed run failed: %s", feed_type, exc)
        run.status = "failed"
        run.error_detail = str(exc)[:2000]

    finally:
        run.completed_at = datetime.now(timezone.utc)
        run.skip_reasons = dict(skip_reasons) if skip_reasons else None

        if not dry_run:
            try:
                db.commit()
            except IntegrityError as exc:
                logger.error("[%s] Final commit failed: %s", feed_type, str(exc)[:200])
                db.rollback()
                run.status = "failed"
                run.error_detail = f"Commit failed: {str(exc)[:200]}"

    stats = {
        "feed_type": feed_type,
        "status": run.status,
        "started_at": run.started_at.isoformat(),
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "items_fetched": run.items_fetched,
        "items_deduped": run.items_deduped,
        "accounts_created": run.accounts_created,
        "accounts_existing": run.accounts_existing,
        "raw_events_created": run.raw_events_created,
        "signals_created": run.signals_created,
        "signals_skipped": run.signals_skipped,
        "errors": run.errors,
        "skip_reasons": dict(skip_reasons),
        "dry_run": dry_run,
    }

    logger.info(
        "[%s] Run complete: fetched=%d deduped=%d accounts_new=%d "
        "raw_events=%d signals=%d skipped=%d errors=%d",
        feed_type,
        run.items_fetched,
        run.items_deduped,
        run.accounts_created,
        run.raw_events_created,
        run.signals_created,
        run.signals_skipped,
        run.errors,
    )

    return stats


def _process_feed_item(
    db: Session,
    workspace_id: uuid.UUID,
    item: FeedItem,
    normalizer: BaseNormalizer,
    run: IngestionRun,
    skip_reasons: dict[str, int],
    seen_external_ids: set[str],
    dry_run: bool,
) -> None:
    """Process a single feed item: resolve account → store raw event → normalize → create signal."""

    # In-batch dedup
    if item.external_id in seen_external_ids:
        run.items_deduped += 1
        skip_reasons["in_batch_duplicate"] += 1
        return
    seen_external_ids.add(item.external_id)

    # DB dedup by external_id
    if _dedup_raw_event_by_external_id(db, item.external_id):
        run.items_deduped += 1
        skip_reasons["already_ingested"] += 1
        return

    # Resolve or create account
    account, was_created = resolve_or_create_account(
        db=db,
        workspace_id=workspace_id,
        ticker=item.ticker,
        company_name=item.company_name,
        domain=item.domain,
    )
    if was_created:
        run.accounts_created += 1
    else:
        run.accounts_existing += 1

    if dry_run:
        logger.info(
            "[DRY RUN] Would create raw_event: %s for %s (%s)",
            item.external_id, item.company_name, "NEW" if was_created else "existing",
        )
        run.raw_events_created += 1
        run.signals_created += 1  # Assume success for dry run
        return

    # Create raw event
    content_hash = RawEvent.compute_content_hash(
        account.id, item.event_type, item.raw_payload or {}
    )
    raw_event = RawEvent(
        workspace_id=workspace_id,
        account_source_id=None,  # Feed-based, not account-source-based
        account_id=account.id,
        event_type=item.event_type,
        raw_payload=item.raw_payload or {},
        source_url=item.source_url,
        external_id=item.external_id,
        content_hash=content_hash,
        occurred_at=item.occurred_at,
        status="pending",
    )
    db.add(raw_event)
    db.flush()
    run.raw_events_created += 1

    # Normalize into signal
    try:
        result = normalizer.normalize(raw_event)
    except SkipEvent as skip:
        reason = str(skip) or "Skipped by normalizer"
        raw_event.status = "skipped"
        raw_event.status_detail = reason[:500]
        run.signals_skipped += 1
        skip_reasons[f"normalizer: {reason[:50]}"] += 1
        return
    except Exception as exc:
        raw_event.status = "failed"
        raw_event.status_detail = str(exc)[:500]
        run.errors += 1
        skip_reasons["normalizer_error"] += 1
        return

    if result is None:
        raw_event.status = "skipped"
        raw_event.status_detail = "Did not qualify as signal"
        run.signals_skipped += 1
        skip_reasons["not_qualified"] += 1
        return

    # Signal-level dedup
    if _dedup_signal(db, account.id, result.signal_type, result.title, result.occurred_at):
        raw_event.status = "skipped"
        raw_event.status_detail = "Duplicate signal exists"
        run.signals_skipped += 1
        skip_reasons["duplicate_signal"] += 1
        return

    # Create signal
    signal = Signal(
        workspace_id=workspace_id,
        account_id=account.id,
        type=result.signal_type,
        title=result.title,
        summary=result.summary,
        occurred_at=result.occurred_at,
        raw_event_id=raw_event.id,
    )
    db.add(signal)
    raw_event.status = "processed"
    run.signals_created += 1
