"""Feed quality validation — structured outbound readiness check.

Pulls the top 15 ranked accounts from the system workspace,
generates outbound-ready fields for each, and assigns internal verdicts.

This is a PURE TRANSFORMATION LAYER. No schema changes. No ingestion changes.
Reads existing dashboard data and produces structured output.

Usage:
    python -m app.jobs.validate_feed_quality
    python -m app.jobs.validate_feed_quality --format json
    python -m app.jobs.validate_feed_quality --limit 10
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone

from app.db import SessionLocal
from app.models import Account, Signal, User, Workspace, WorkspaceMember
from app.services.scoring import (
    compute_account_score,
    opportunity_probability,
    signal_score_contribution,
    days_ago,
)
from sqlalchemy import select

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

SYSTEM_WORKSPACE_ID = uuid.UUID("cccccccc-0000-0000-0000-000000000001")


# --- Verdict thresholds ---
# Based on score, recency, and signal quality.
# Strong: score >= 25, signal <= 15 days old, clear outbound angle
# Mediocre: score >= 15, or signal is 16-35 days old
# Junk: everything else

@dataclass
class OutboundOpportunity:
    rank: int
    company: str
    ticker: str | None
    opportunity_score: float
    opportunity_probability: float
    signal_summary: str
    why_it_matters: str
    recommended_contact_title: str
    outreach_angle: str
    urgency: str
    verdict: str  # strong | mediocre | junk
    verdict_reason: str


def _signal_summary(account: Account) -> str:
    """One-line summary of the account's signals."""
    signals = sorted(account.signals, key=lambda s: s.occurred_at, reverse=True)
    if not signals:
        return "No signals detected."

    parts = []
    for s in signals:
        age = days_ago(s.occurred_at)
        parts.append(f"{s.title} ({age}d ago)")
    return "; ".join(parts)


def _why_it_matters(account: Account) -> str:
    """Deterministic reasoning about why this account matters for outbound."""
    signals = sorted(account.signals, key=lambda s: s.occurred_at, reverse=True)
    if not signals:
        return "No actionable signal."

    latest = signals[0]
    payload = {}

    # Try to get raw payload from the linked raw event
    if latest.raw_event_id and hasattr(latest, "raw_event_id"):
        # We'll work from the signal's own data
        pass

    title = latest.title
    age = days_ago(latest.occurred_at)

    if "Acquiring" in title:
        target = title.replace("Acquiring ", "")
        return (
            f"Active acquirer — deploying capital to acquire {target}. "
            f"Acquirers restructure vendor relationships, consolidate tooling, "
            f"and expand headcount post-close. Signal is {age} days fresh."
        )
    elif "Being acquired by" in title:
        acquirer = title.replace("Being acquired by ", "")
        return (
            f"Acquisition target — being absorbed by {acquirer}. "
            f"Targets undergo tool migration, team restructuring, and budget reallocation "
            f"during integration. New decision-makers emerge. Signal is {age} days fresh."
        )
    else:
        return f"M&A activity detected: {title}. Signal is {age} days fresh."


def _recommended_contact_title(account: Account) -> str:
    """Deterministic contact title recommendation based on signal type."""
    signals = sorted(account.signals, key=lambda s: s.occurred_at, reverse=True)
    if not signals:
        return "VP of Operations"

    latest = signals[0]
    title = latest.title

    if "Acquiring" in title:
        # Acquirer — talk to the person managing integration
        return "VP of Corporate Development / Head of M&A Integration"
    elif "Being acquired by" in title:
        # Target — talk to someone who controls vendor decisions during transition
        return "CTO / VP of Engineering / Head of IT"
    else:
        return "VP of Operations"


def _outreach_angle(account: Account) -> str:
    """Deterministic outreach angle based on signal content."""
    signals = sorted(account.signals, key=lambda s: s.occurred_at, reverse=True)
    if not signals:
        return "No clear angle."

    latest = signals[0]
    title = latest.title
    company = account.name

    if "Acquiring" in title:
        target = title.replace("Acquiring ", "")
        return (
            f"Congrats on the {target} acquisition. As you integrate teams and systems, "
            f"companies in your position typically reassess [your category]. "
            f"Would it make sense to explore how we help post-acquisition consolidation?"
        )
    elif "Being acquired by" in title:
        acquirer = title.replace("Being acquired by ", "")
        return (
            f"Saw the news about {acquirer} acquiring {company}. During integration, "
            f"teams often get new budget and mandate to standardize tooling. "
            f"We've helped similar companies navigate this transition — worth a quick chat?"
        )
    else:
        return f"Recent M&A activity at {company} suggests organizational change."


def _urgency(account: Account, score: float) -> str:
    """Urgency level based on recency and score."""
    signals = sorted(account.signals, key=lambda s: s.occurred_at, reverse=True)
    if not signals:
        return "low"

    latest_age = days_ago(signals[0].occurred_at)

    if latest_age <= 7 and score >= 25:
        return "high — reach out this week"
    elif latest_age <= 15 and score >= 20:
        return "medium-high — reach out within 2 weeks"
    elif latest_age <= 30 and score >= 15:
        return "medium — reach out this month"
    elif latest_age <= 45:
        return "low-medium — monitor, not urgent"
    else:
        return "low — stale signal"


def _verdict(account: Account, score: float) -> tuple[str, str]:
    """Assign internal verdict: strong, mediocre, or junk."""
    signals = sorted(account.signals, key=lambda s: s.occurred_at, reverse=True)
    if not signals:
        return "junk", "No signals."

    latest = signals[0]
    age = days_ago(latest.occurred_at)

    # Strong: fresh signal (<=15d), high score (>=25), clear M&A role
    if age <= 15 and score >= 25:
        return "strong", (
            f"Fresh signal ({age}d), high score ({score}), "
            f"clear M&A event with actionable outbound angle."
        )

    # Also strong: very fresh (<=7d) even with moderate score
    if age <= 7 and score >= 20:
        return "strong", (
            f"Very fresh signal ({age}d), decent score ({score}). "
            f"Recency alone makes this worth pursuing."
        )

    # Mediocre: moderate freshness or moderate score
    if age <= 30 and score >= 15:
        return "mediocre", (
            f"Signal is {age}d old with score {score}. "
            f"Outbound is possible but timing advantage is fading."
        )

    if age <= 45 and score >= 10:
        return "mediocre", (
            f"Signal aging ({age}d), score is {score}. "
            f"Still has context but urgency is low."
        )

    # Junk: old signal or low score
    return "junk", (
        f"Signal is {age}d old, score is {score}. "
        f"Too stale for cold outbound — no timing advantage."
    )


def validate_feed(limit: int = 15) -> list[OutboundOpportunity]:
    """Pull top N accounts and generate outbound opportunities."""
    db = SessionLocal()
    try:
        accounts = db.scalars(
            select(Account).where(Account.workspace_id == SYSTEM_WORKSPACE_ID)
        ).all()

        if not accounts:
            logger.warning("No accounts in system workspace %s", SYSTEM_WORKSPACE_ID)
            return []

        # Score and rank (same logic as dashboard endpoint)
        scored = []
        for acct in accounts:
            score = compute_account_score(acct.signals)
            scored.append((acct, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        top = scored[:limit]

        results = []
        for rank, (acct, score) in enumerate(top, 1):
            prob = opportunity_probability(score)
            v, v_reason = _verdict(acct, score)

            results.append(OutboundOpportunity(
                rank=rank,
                company=acct.name,
                ticker=acct.ticker,
                opportunity_score=score,
                opportunity_probability=prob,
                signal_summary=_signal_summary(acct),
                why_it_matters=_why_it_matters(acct),
                recommended_contact_title=_recommended_contact_title(acct),
                outreach_angle=_outreach_angle(acct),
                urgency=_urgency(acct, score),
                verdict=v,
                verdict_reason=v_reason,
            ))

        return results

    finally:
        db.close()


def _print_table(opportunities: list[OutboundOpportunity]) -> None:
    """Print human-readable table of outbound opportunities."""
    sep = "=" * 100

    # Summary header
    verdicts = {"strong": 0, "mediocre": 0, "junk": 0}
    for o in opportunities:
        verdicts[o.verdict] += 1

    print(f"\n{sep}")
    print("FEED QUALITY VALIDATION REPORT")
    print(f"Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"Accounts evaluated: {len(opportunities)}")
    print(f"Verdicts:  STRONG={verdicts['strong']}  MEDIOCRE={verdicts['mediocre']}  JUNK={verdicts['junk']}")
    print(sep)

    for o in opportunities:
        verdict_icon = {"strong": "[OK]", "mediocre": "[~~]", "junk": "[XX]"}[o.verdict]
        print(f"\n{'─' * 100}")
        print(f"#{o.rank}  {verdict_icon}  {o.company} ({o.ticker or 'private'})")
        print(f"     Score: {o.opportunity_score}  |  Probability: {o.opportunity_probability}  |  Urgency: {o.urgency}")
        print(f"     Signal:  {o.signal_summary}")
        print(f"     Why:     {o.why_it_matters}")
        print(f"     Contact: {o.recommended_contact_title}")
        print(f"     Angle:   {o.outreach_angle}")
        print(f"     Verdict: {o.verdict.upper()} — {o.verdict_reason}")

    print(f"\n{sep}")
    print("END OF REPORT")
    print(sep)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate feed quality for outbound readiness"
    )
    parser.add_argument(
        "--format",
        choices=["table", "json"],
        default="table",
        help="Output format (default: table)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=15,
        help="Number of top accounts to evaluate (default: 15)",
    )
    args = parser.parse_args()

    opportunities = validate_feed(limit=args.limit)

    if not opportunities:
        print("No accounts found in system workspace. Run the daily feed first:")
        print("  python -m app.jobs.daily_feed")
        sys.exit(1)

    if args.format == "json":
        print(json.dumps([asdict(o) for o in opportunities], indent=2, default=str))
    else:
        _print_table(opportunities)


if __name__ == "__main__":
    main()
