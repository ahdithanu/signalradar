from datetime import datetime, timezone

SIGNAL_WEIGHTS: dict[str, float] = {
    "funding": 30.0,
    "product_launch": 25.0,
    "positioning_shift": 22.0,
    "hiring": 20.0,
    "partnership": 18.0,
    "growth": 15.0,
}

# Day bucket multipliers per signal type.
# Each list is checked in order; first matching bucket wins.
# Format: (max_days_inclusive, multiplier)
RECENCY_BUCKETS: dict[str, list[tuple[int, float]]] = {
    "funding": [
        (10, 1.00),
        (15, 0.90),
        (30, 0.75),
        (45, 0.55),
        (60, 0.35),
    ],
    "positioning_shift": [
        (10, 1.00),
        (20, 0.85),
        (35, 0.65),
        (60, 0.40),
    ],
    "hiring": [
        (10, 0.90),
        (20, 0.75),
        (35, 0.55),
        (60, 0.35),
    ],
    "product_launch": [
        (10, 0.95),
        (20, 0.80),
        (35, 0.60),
        (60, 0.35),
    ],
    "partnership": [
        (10, 0.85),
        (20, 0.70),
        (35, 0.50),
        (60, 0.30),
    ],
    "growth": [
        (10, 0.75),
        (20, 0.60),
        (35, 0.45),
        (60, 0.25),
    ],
}

# Fallback multipliers for the 61+ bucket per type
RECENCY_FLOOR: dict[str, float] = {
    "funding": 0.15,
    "positioning_shift": 0.20,
    "hiring": 0.15,
    "product_launch": 0.15,
    "partnership": 0.10,
    "growth": 0.10,
}

DEFAULT_FLOOR = 0.10


def days_ago(occurred_at: datetime) -> int:
    now = datetime.now(timezone.utc)
    return max(0, (now - occurred_at).days)


def recency_multiplier(signal_type: str, occurred_at: datetime) -> float:
    d = days_ago(occurred_at)
    buckets = RECENCY_BUCKETS.get(signal_type)
    if buckets:
        for max_days, mult in buckets:
            if d <= max_days:
                return mult
    return RECENCY_FLOOR.get(signal_type, DEFAULT_FLOOR)


def freshness_bonus(occurred_at: datetime) -> float:
    d = days_ago(occurred_at)
    if d <= 10:
        return 1.15
    if d <= 20:
        return 1.05
    return 1.00


def signal_score_contribution(signal_type: str, occurred_at: datetime) -> float:
    weight = SIGNAL_WEIGHTS.get(signal_type, 10.0)
    mult = recency_multiplier(signal_type, occurred_at)
    bonus = freshness_bonus(occurred_at)
    return round(weight * mult * bonus, 1)


def compute_account_score(signals: list) -> float:
    """Compute total opportunity score for an account from its signals."""
    total = 0.0
    for s in signals:
        total += signal_score_contribution(s.type, s.occurred_at)
    return round(total, 1)


def opportunity_probability(score: float) -> float:
    return round(min(score / 100.0, 1.0), 2)


def enhance_why_now(stored_why_now: str | None, signals: list) -> str | None:
    """If a positioning_shift signal exists, prepend GTM/ICP change context."""
    shift_signals = [s for s in signals if s.type == "positioning_shift"]
    if not shift_signals:
        return stored_why_now
    most_recent = max(shift_signals, key=lambda s: s.occurred_at)
    prefix = f"Active positioning shift detected: {most_recent.title}."
    if stored_why_now:
        return f"{prefix} {stored_why_now}"
    return prefix
