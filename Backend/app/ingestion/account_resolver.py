"""Account resolution for feed-based ingestion.

Given a ticker, company name, and optional domain from a feed item,
find an existing Account or create a new one.

Resolution order (strict, no fuzzy matching):
  1. Ticker exact match (case-insensitive)
  2. Domain exact match (case-insensitive)
  3. Normalized company name exact match (case-insensitive, stripped suffixes)
  4. No match → create new Account

Returns (account, created: bool).
"""

from __future__ import annotations

import logging
import re
import uuid

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.account import Account

logger = logging.getLogger(__name__)

# Suffixes to strip for name normalization.
# "IonQ, Inc." → "ionq", "Salesforce, Inc." → "salesforce"
_NAME_SUFFIXES = re.compile(
    r",?\s*(?:Inc\.?|Corp\.?|Corporation|Ltd\.?|Limited|LLC|L\.?P\.?|PLC|S\.?A\.?|N\.?V\.?|Holdings|Group|Co\.?)$",
    re.IGNORECASE,
)


def _normalize_name(name: str) -> str:
    """Strip corporate suffixes and normalize for comparison."""
    cleaned = _NAME_SUFFIXES.sub("", name).strip()
    # Remove trailing punctuation
    cleaned = cleaned.rstrip(".,;")
    return cleaned.lower()


def _extract_domain_from_url(url: str) -> str | None:
    """Extract bare domain from a URL like 'https://www.ionq.com' → 'ionq.com'."""
    if not url:
        return None
    # Remove protocol
    domain = url.split("://", 1)[-1]
    # Remove path
    domain = domain.split("/", 1)[0]
    # Remove www.
    if domain.startswith("www."):
        domain = domain[4:]
    return domain.lower() if domain else None


def resolve_or_create_account(
    db: Session,
    workspace_id: uuid.UUID,
    ticker: str | None,
    company_name: str,
    domain: str | None = None,
) -> tuple[Account, bool]:
    """Resolve an existing account or create a new one.

    Returns (account, was_created).
    """
    # 1. Ticker exact match
    if ticker:
        account = db.scalar(
            select(Account).where(
                Account.workspace_id == workspace_id,
                func.lower(Account.ticker) == ticker.lower(),
            )
        )
        if account:
            logger.debug("Resolved by ticker: %s → %s", ticker, account.name)
            return account, False

    # 2. Domain exact match
    if domain:
        account = db.scalar(
            select(Account).where(
                Account.workspace_id == workspace_id,
                func.lower(Account.domain) == domain.lower(),
            )
        )
        if account:
            # Backfill ticker if we have one and the account doesn't
            if ticker and not account.ticker:
                account.ticker = ticker.upper()
                db.flush()
            logger.debug("Resolved by domain: %s → %s", domain, account.name)
            return account, False

    # 3. Normalized name exact match
    normalized = _normalize_name(company_name)
    if normalized:
        # Load candidates and compare in Python to use our normalization
        candidates = db.scalars(
            select(Account).where(
                Account.workspace_id == workspace_id,
                func.lower(Account.name).ilike(f"%{normalized[:3]}%"),
            )
        ).all()
        for candidate in candidates:
            if _normalize_name(candidate.name) == normalized:
                # Backfill missing fields
                if ticker and not candidate.ticker:
                    candidate.ticker = ticker.upper()
                if domain and not candidate.domain:
                    candidate.domain = domain
                db.flush()
                logger.debug("Resolved by name: %s → %s", company_name, candidate.name)
                return candidate, False

    # 4. No match → create
    account = Account(
        workspace_id=workspace_id,
        name=company_name,
        ticker=ticker.upper() if ticker else None,
        domain=domain,
        status="New",
    )
    db.add(account)
    db.flush()
    logger.info("Created new account: %s (ticker=%s, domain=%s)", company_name, ticker, domain)
    return account, True
