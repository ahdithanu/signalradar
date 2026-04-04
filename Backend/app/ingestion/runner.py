"""Ingestion runner — orchestrates extract → store → normalize.

This module contains no business logic. It coordinates extractors and
normalizers, manages database writes, and handles errors per-source.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.account_source import AccountSource
from app.models.raw_event import RawEvent
from app.models.signal import Signal
from app.ingestion.extractors.base import BaseExtractor, ExtractedEvent
from app.ingestion.normalizers.base import BaseNormalizer, SkipEvent

logger = logging.getLogger(__name__)

# Map source_type → extractor class, event_type → normalizer class
# Populated by register functions below.
_EXTRACTORS: dict[str, BaseExtractor] = {}
_NORMALIZERS: dict[str, BaseNormalizer] = {}


def register_extractor(source_type: str, extractor: BaseExtractor) -> None:
    _EXTRACTORS[source_type] = extractor


def register_normalizer(event_type: str, normalizer: BaseNormalizer) -> None:
    _NORMALIZERS[event_type] = normalizer


def _dedup_raw_event(
    db: Session, event: ExtractedEvent
) -> bool:
    """Return True if this event already exists (should be skipped)."""
    if event.external_id:
        exists = db.scalar(
            select(RawEvent.id).where(RawEvent.external_id == event.external_id)
        )
        if exists:
            return True

    # Fallback: content hash dedup
    content_hash = RawEvent.compute_content_hash(
        event.account_id, event.event_type, event.raw_payload
    )
    exists = db.scalar(
        select(RawEvent.id).where(RawEvent.content_hash == content_hash)
    )
    return exists is not None


def _dedup_signal(
    db: Session,
    account_id: uuid.UUID,
    signal_type: str,
    title: str,
    occurred_at: datetime,
) -> bool:
    """Return True if a similar signal already exists for this account."""
    window_start = occurred_at - timedelta(days=7)
    window_end = occurred_at + timedelta(days=7)
    exists = db.scalar(
        select(Signal.id).where(
            and_(
                Signal.account_id == account_id,
                Signal.type == signal_type,
                Signal.title == title,
                Signal.occurred_at >= window_start,
                Signal.occurred_at <= window_end,
            )
        )
    )
    return exists is not None


def run_extraction(
    db: Session,
    source_type: str,
    account_id: uuid.UUID | None = None,
    limit: int | None = None,
    dry_run: bool = False,
) -> dict:
    """Run extraction for all active sources of a given type.

    Returns stats dict: {sources_checked, events_extracted, events_deduped, events_stored}.
    """
    extractor = _EXTRACTORS.get(source_type)
    if not extractor:
        logger.error("No extractor registered for source_type=%s", source_type)
        return {"error": f"No extractor for {source_type}"}

    query = select(AccountSource).where(
        and_(
            AccountSource.source_type == source_type,
            AccountSource.is_active == True,  # noqa: E712
        )
    )
    if account_id:
        query = query.where(AccountSource.account_id == account_id)
    if limit:
        query = query.limit(limit)

    sources = db.scalars(query).all()
    stats = {
        "sources_checked": 0,
        "events_extracted": 0,
        "events_deduped": 0,
        "events_stored": 0,
        "events_errored": 0,
    }

    # Track external_ids and content_hashes seen within this batch
    # to catch duplicates before they hit the DB unique constraint.
    seen_external_ids: set[str] = set()
    seen_content_hashes: set[str] = set()

    for source in sources:
        stats["sources_checked"] += 1
        try:
            events = extractor.extract(source)
        except Exception as exc:
            logger.error(
                "Extractor failed for source %s: %s", source.id, exc
            )
            source.last_error = str(exc)[:500]
            source.last_checked_at = datetime.now(timezone.utc)
            db.commit()
            continue

        source.last_checked_at = datetime.now(timezone.utc)
        source.last_error = None

        for event_data in events:
            stats["events_extracted"] += 1

            # In-batch dedup: external_id
            if event_data.external_id and event_data.external_id in seen_external_ids:
                logger.info(
                    "In-batch dedup: external_id=%s already seen this run",
                    event_data.external_id,
                )
                stats["events_deduped"] += 1
                continue

            # DB dedup
            if _dedup_raw_event(db, event_data):
                stats["events_deduped"] += 1
                continue

            content_hash = RawEvent.compute_content_hash(
                event_data.account_id,
                event_data.event_type,
                event_data.raw_payload,
            )

            # In-batch dedup: content_hash
            if content_hash in seen_content_hashes:
                logger.info(
                    "In-batch dedup: content_hash=%s already seen this run",
                    content_hash[:16],
                )
                stats["events_deduped"] += 1
                continue

            if dry_run:
                stats["events_stored"] += 1
                if event_data.external_id:
                    seen_external_ids.add(event_data.external_id)
                seen_content_hashes.add(content_hash)
                logger.info(
                    "[DRY RUN] Would store event: %s %s",
                    event_data.event_type,
                    event_data.external_id,
                )
                continue

            # Resolve workspace_id from the source's account
            workspace_id = source.workspace_id

            raw_event = RawEvent(
                workspace_id=workspace_id,
                account_source_id=event_data.account_source_id,
                account_id=event_data.account_id,
                event_type=event_data.event_type,
                raw_payload=event_data.raw_payload,
                source_url=event_data.source_url,
                external_id=event_data.external_id,
                content_hash=content_hash,
                occurred_at=event_data.occurred_at,
                status="pending",
            )
            db.add(raw_event)

            # Track for in-batch dedup
            if event_data.external_id:
                seen_external_ids.add(event_data.external_id)
            seen_content_hashes.add(content_hash)
            stats["events_stored"] += 1

        # Commit per-source with safety net for unexpected constraint violations
        try:
            db.commit()
        except IntegrityError as exc:
            logger.error(
                "IntegrityError storing events for source %s: %s — rolling back",
                source.id,
                str(exc)[:200],
            )
            db.rollback()
            stats["events_errored"] += 1

    logger.info(
        "Extraction complete for %s: sources=%d fetched=%d deduped=%d stored=%d",
        source_type,
        stats["sources_checked"],
        stats["events_extracted"],
        stats["events_deduped"],
        stats["events_stored"],
    )
    return stats


def run_normalization(
    db: Session,
    event_type: str | None = None,
    dry_run: bool = False,
) -> dict:
    """Normalize all pending raw events into signals.

    Returns stats dict: {events_processed, signals_created, events_skipped, events_failed}.
    """
    query = select(RawEvent).where(RawEvent.status == "pending")
    if event_type:
        query = query.where(RawEvent.event_type == event_type)
    query = query.order_by(RawEvent.fetched_at.asc())

    pending = db.scalars(query).all()
    stats = {
        "events_processed": 0,
        "signals_created": 0,
        "events_skipped": 0,
        "events_failed": 0,
    }

    # Track signals created this batch to catch in-batch duplicates.
    # Key: (account_id, signal_type, title)
    seen_signals: set[tuple[uuid.UUID, str, str]] = set()

    for raw_event in pending:
        stats["events_processed"] += 1
        normalizer = _NORMALIZERS.get(raw_event.event_type)
        if not normalizer:
            logger.warning(
                "No normalizer for event_type=%s (event %s)",
                raw_event.event_type,
                raw_event.id,
            )
            raw_event.status = "skipped"
            raw_event.status_detail = f"No normalizer for {raw_event.event_type}"
            stats["events_skipped"] += 1
            continue

        try:
            result = normalizer.normalize(raw_event)
        except SkipEvent as skip:
            reason = str(skip) or "Skipped by normalizer (no reason given)"
            logger.info(
                "Normalizer skipped raw_event %s: %s", raw_event.id, reason
            )
            raw_event.status = "skipped"
            raw_event.status_detail = reason[:500]
            stats["events_skipped"] += 1
            continue
        except Exception as exc:
            logger.error(
                "Normalizer failed for raw_event %s: %s", raw_event.id, exc
            )
            raw_event.status = "failed"
            raw_event.status_detail = str(exc)[:500]
            stats["events_failed"] += 1
            continue

        if result is None:
            raw_event.status = "skipped"
            raw_event.status_detail = "Did not qualify as signal"
            stats["events_skipped"] += 1
            continue

        # In-batch signal dedup
        signal_key = (raw_event.account_id, result.signal_type, result.title)
        if signal_key in seen_signals:
            logger.info(
                "In-batch signal dedup: %s for account %s",
                result.title,
                raw_event.account_id,
            )
            raw_event.status = "skipped"
            raw_event.status_detail = "Duplicate signal in same batch"
            stats["events_skipped"] += 1
            continue

        # DB signal dedup (against previously committed signals)
        if _dedup_signal(
            db,
            raw_event.account_id,
            result.signal_type,
            result.title,
            result.occurred_at,
        ):
            raw_event.status = "skipped"
            raw_event.status_detail = "Duplicate signal exists"
            stats["events_skipped"] += 1
            continue

        if dry_run:
            logger.info(
                "[DRY RUN] Would create signal: type=%s title=%s",
                result.signal_type,
                result.title,
            )
            raw_event.status = "processed"
            seen_signals.add(signal_key)
            stats["signals_created"] += 1
            continue

        signal = Signal(
            workspace_id=raw_event.workspace_id,
            account_id=raw_event.account_id,
            type=result.signal_type,
            title=result.title,
            summary=result.summary,
            occurred_at=result.occurred_at,
            raw_event_id=raw_event.id,
        )
        db.add(signal)
        raw_event.status = "processed"
        raw_event.status_detail = None
        seen_signals.add(signal_key)
        stats["signals_created"] += 1

    db.commit()
    logger.info(
        "Normalization complete: processed=%d signals_created=%d skipped=%d failed=%d",
        stats["events_processed"],
        stats["signals_created"],
        stats["events_skipped"],
        stats["events_failed"],
    )
    return stats


def run_pipeline(
    db: Session,
    source_type: str,
    event_type: str,
    account_id: uuid.UUID | None = None,
    limit: int | None = None,
    dry_run: bool = False,
) -> dict:
    """Run extraction then normalization for a signal type end-to-end."""
    extract_stats = run_extraction(
        db,
        source_type=source_type,
        account_id=account_id,
        limit=limit,
        dry_run=dry_run,
    )
    normalize_stats = run_normalization(
        db,
        event_type=event_type,
        dry_run=dry_run,
    )
    return {"extraction": extract_stats, "normalization": normalize_stats}
