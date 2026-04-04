"""Positioning shift normalizer.

Transforms raw website_change events into product-layer positioning_shift
signals with executive-readable titles and actionable GTM interpretations.

QUALITY GATE — the "salesperson outbound test":
    Before creating any signal, this normalizer asks:
    "Would a salesperson change their outreach because of this?"
    If the answer is no, the event is skipped.

A positioning_shift signal must indicate a meaningful change in:
  - ICP (who they sell to) — e.g. SMB → enterprise
  - GTM motion (how they sell) — e.g. self-serve → sales-led
  - Product positioning (what they emphasize) — e.g. tool → platform

Skip rules — do NOT create signals for:
  1. Blog posts, legal pages, status pages, careers, about pages
  2. Footer-only or copyright-only changes
  3. Minor copy edits (diff < 15%)
  4. Low or missing change_significance
  5. No GTM-relevant keywords
  6. Empty diffs (no content or no changed sections)
  7. Generic product updates with no ICP/GTM implication
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.models.raw_event import RawEvent
from app.ingestion.normalizers.base import NormalizedSignal, SkipEvent

logger = logging.getLogger(__name__)

# ── Page types that NEVER produce positioning_shift signals ──────────────
_NOISE_PAGE_TYPES = frozenset({
    "blog", "legal", "status", "careers", "about", "other",
    "changelog", "release_notes", "support", "docs",
})

# ── Section names that indicate noise, not positioning change ────────────
_NOISE_SECTIONS = frozenset({
    "footer", "copyright", "blog_listing", "cookie_banner",
    "nav", "sidebar",
})

# ── GTM keyword categories ──────────────────────────────────────────────
# Each keyword maps to a category that determines interpretation framing.
_GTM_KEYWORD_CATEGORIES: dict[str, str] = {
    # ICP upmarket shifts
    "enterprise": "icp_upmarket",
    "mid-market": "icp_upmarket",
    "upmarket": "icp_upmarket",
    "regulated industries": "icp_upmarket",
    "fortune 500": "icp_upmarket",
    "platform": "icp_upmarket",
    # Sales motion shifts
    "contact sales": "gtm_sales_led",
    "talk to": "gtm_sales_led",
    "schedule a consultation": "gtm_sales_led",
    "request a demo": "gtm_sales_led",
    "custom pricing": "gtm_sales_led",
    "dedicated account manager": "gtm_sales_led",
    "sla": "gtm_sales_led",
    "security advisor": "gtm_sales_led",
    "sales team": "gtm_sales_led",
    "enterprise pilot": "gtm_sales_led",
    "team trial": "gtm_sales_led",
    # Vertical expansion
    "financial services": "new_vertical",
    "healthcare": "new_vertical",
    "hospital": "new_vertical",
    "hospital systems": "new_vertical",
    "health system": "new_vertical",
    "banks": "new_vertical",
    "fintech": "new_vertical",
    "insurance": "new_vertical",
    "government": "new_vertical",
    # Geographic expansion
    "emea": "new_market",
    "europe": "new_market",
    "apac": "new_market",
    "cross-border": "new_market",
    "emea sales team": "new_market",
    # Compliance / trust (supports upmarket shift)
    "soc 2": "compliance",
    "fedramp": "compliance",
    "hipaa": "compliance",
    "pci dss": "compliance",
    "gdpr": "compliance",
    # Team/org targeting (individual → team shift)
    "data teams": "icp_upmarket",
    "collaborate": "icp_upmarket",
    "organization": "icp_upmarket",
    "governed metrics": "icp_upmarket",
    "role-based access": "icp_upmarket",
}


def _match_gtm_keywords(extracted: list[str] | None) -> list[tuple[str, str]]:
    """Return matched (keyword, category) pairs from extracted keywords.

    Matches longest GTM keyword first to avoid partial-match collisions
    (e.g. "EMEA sales team" must match new_market, not gtm_sales_led
    via the shorter "sales team" substring).
    """
    if not extracted or not isinstance(extracted, list):
        return []

    # Sort GTM keywords longest-first so "emea sales team" matches
    # before "sales team".
    sorted_gtm = sorted(
        _GTM_KEYWORD_CATEGORIES.items(), key=lambda x: len(x[0]), reverse=True
    )

    matches: list[tuple[str, str]] = []
    seen_cats: set[str] = set()
    for kw in extracted:
        if not isinstance(kw, str):
            continue
        kw_lower = kw.lower().strip()
        for gtm_kw, cat in sorted_gtm:
            # Match if: exact match, or GTM keyword is a substring of
            # the extracted keyword (e.g. "enterprise" in "enterprise pilot").
            # Do NOT match the reverse — "enterprise" should not match
            # "enterprise pilot" when extracted_kw is "enterprise".
            if kw_lower == gtm_kw or gtm_kw in kw_lower:
                if cat not in seen_cats or cat in ("new_vertical", "compliance"):
                    matches.append((kw, cat))
                    seen_cats.add(cat)
                break
    return matches


def _dominant_shift_type(
    matches: list[tuple[str, str]], page_type: str | None = None,
) -> str | None:
    """Determine the primary shift type from keyword matches and page context."""
    if not matches:
        return None
    cats = [cat for _, cat in matches]
    cat_set = set(cats)

    # Context-aware: pricing pages with sales keywords → gtm_sales_led
    # regardless of whether "enterprise" also appears.
    if page_type == "pricing" and "gtm_sales_led" in cat_set:
        return "gtm_sales_led"

    # Priority order: new_vertical > icp_upmarket > gtm_sales_led > new_market
    for priority in ("new_vertical", "icp_upmarket", "gtm_sales_led", "new_market"):
        if priority in cat_set:
            return priority
    return cats[0]


def _is_noise_page(page_type: str | None) -> bool:
    if not page_type:
        return False
    return page_type.lower().strip() in _NOISE_PAGE_TYPES


def _is_noise_sections(sections: list | None) -> bool:
    """Return True if ALL changed sections are noise."""
    if not sections or not isinstance(sections, list):
        return False
    clean = {s.lower().strip() for s in sections if isinstance(s, str)}
    return bool(clean) and clean.issubset(_NOISE_SECTIONS)


# ── Title builders per shift type ────────────────────────────────────────

def _build_title(shift_type: str, page_type: str | None,
                 matches: list[tuple[str, str]],
                 previous_text: str | None,
                 current_text: str | None) -> str:
    """Crisp, executive-readable title."""

    if shift_type == "new_vertical":
        verticals = [kw for kw, cat in matches if cat == "new_vertical"]
        if verticals:
            return f"Launched {verticals[0].lower()} vertical — expanding ICP"
        return "New vertical landing page added"

    if shift_type == "new_market":
        markets = [kw for kw, cat in matches if cat == "new_market"]
        if markets:
            return f"Expanding into {markets[0]} — new geographic market"
        return "New geographic market page launched"

    if shift_type == "gtm_sales_led":
        if page_type == "pricing":
            return "Pricing restructured — shifting to sales-led GTM"
        return "GTM motion shifting from self-serve to sales-assisted"

    if shift_type == "icp_upmarket":
        # Detect tool→platform shift
        if previous_text and current_text:
            prev_l = previous_text.lower()
            curr_l = current_text.lower()
            if ("tool" in prev_l or "simple" in prev_l) and "platform" in curr_l:
                return "Repositioning from tool to platform — moving upmarket"
            if any(w in prev_l for w in ("small", "individual", "personal")) and \
               any(w in curr_l for w in ("enterprise", "team", "organization")):
                return "ICP shifting upmarket — enterprise positioning adopted"
        return "Website messaging shifted to enterprise positioning"

    return "Significant positioning change detected on website"


# ── Interpretation builders ──────────────────────────────────────────────

def _build_interpretation(shift_type: str, page_type: str | None,
                          matches: list[tuple[str, str]],
                          previous_text: str | None,
                          current_text: str | None) -> str:
    """Actionable GTM interpretation — answers "so what?" for a salesperson.

    This becomes the `interpretation` field in the dashboard. It must tell
    a salesperson WHY this matters and HOW to adjust their approach.
    """

    if shift_type == "new_vertical":
        verticals = [kw for kw, cat in matches if cat == "new_vertical"]
        vert_name = verticals[0] if verticals else "a new vertical"
        has_sales_cta = any(cat == "gtm_sales_led" for _, cat in matches)
        parts = [
            f"Company is actively investing in {vert_name} — this is not a blog post, it's a dedicated solutions page.",
        ]
        if has_sales_cta:
            parts.append("Page includes a sales CTA, indicating they're ready to engage buyers in this space.")
        parts.append(f"Outbound angle: reference their {vert_name} push and position around industry-specific pain points.")
        return " ".join(parts)

    if shift_type == "new_market":
        markets = [kw for kw, cat in matches if cat == "new_market"]
        market_name = markets[0] if markets else "a new region"
        return (
            f"Company is expanding into {market_name} with a dedicated market page and local sales presence. "
            f"This signals budget allocation for regional growth. "
            f"Outbound angle: lead with how you help companies scale in new markets — localization, compliance, or regional ops."
        )

    if shift_type == "gtm_sales_led":
        if page_type == "pricing":
            has_enterprise = any("enterprise" in kw.lower() for kw, _ in matches)
            enterprise_note = " They added an enterprise tier with custom pricing." if has_enterprise else ""
            return (
                f"Pricing page removed self-serve options and added 'Contact Sales.'{enterprise_note} "
                f"This means they're building a sales org and investing in higher-touch deals. "
                f"Outbound angle: they're actively hiring or tooling up for sales-led growth — offer to accelerate that motion."
            )
        return (
            "Website now pushes visitors toward sales conversations instead of self-serve signup. "
            "This indicates a GTM motion shift — they're investing in sales infrastructure. "
            "Outbound angle: reference their move to sales-led and position around sales enablement, pipeline, or deal acceleration."
        )

    if shift_type == "icp_upmarket":
        has_compliance = any(cat == "compliance" for _, cat in matches)
        compliance_note = ""
        if has_compliance:
            certs = [kw for kw, cat in matches if cat == "compliance"]
            compliance_note = f" They're now highlighting {', '.join(certs)}, signaling readiness for regulated buyers."

        if previous_text and current_text:
            prev_l = previous_text.lower()
            if any(w in prev_l for w in ("small", "individual", "simple", "personal")):
                return (
                    f"Homepage rewrote from SMB/individual messaging to enterprise positioning.{compliance_note} "
                    f"This is a deliberate ICP shift — they're chasing larger deals with longer sales cycles. "
                    f"Outbound angle: acknowledge their upmarket move and position around enterprise readiness challenges — procurement, security reviews, multi-stakeholder selling."
                )

        return (
            f"Website now targets enterprise buyers with platform-level messaging.{compliance_note} "
            f"This signals a strategic shift in who they're selling to. "
            f"Outbound angle: reference their enterprise push and lead with how you help companies navigate the SMB-to-enterprise transition."
        )

    return "Positioning change detected — review the website diff for GTM implications."


class PositioningNormalizer:
    """Normalizes website_change raw events into positioning_shift signals.

    Every signal that passes must answer YES to:
    "Would a salesperson change their outreach because of this?"
    """

    def normalize(self, event: RawEvent) -> NormalizedSignal | None:
        if event.event_type != "website_change":
            return None

        payload = event.raw_payload
        if not isinstance(payload, dict):
            raise SkipEvent(
                f"Invalid payload type: {type(payload).__name__}"
            )

        page_type = payload.get("page_type")
        previous_text = payload.get("previous_text")
        current_text = payload.get("current_text")
        changed_sections = payload.get("changed_sections")
        extracted_keywords = payload.get("extracted_keywords")
        change_significance = payload.get("change_significance")
        diff_percentage = payload.get("diff_percentage")

        # ── Skip rule 1: noise page types ────────────────────────
        if _is_noise_page(page_type):
            raise SkipEvent(f"Noise page type: {page_type}")

        # ── Skip rule 2: no content to analyze ───────────────────
        if not current_text and not changed_sections:
            raise SkipEvent("No current_text and no changed_sections")

        # ── Skip rule 3: empty changed sections ──────────────────
        if isinstance(changed_sections, list) and len(changed_sections) == 0:
            raise SkipEvent("Empty changed_sections list")

        # ── Skip rule 4: noise-only sections ─────────────────────
        if _is_noise_sections(changed_sections):
            raise SkipEvent(f"Only noise sections: {changed_sections}")

        # ── Skip rule 5: minor copy edit ─────────────────────────
        if diff_percentage is not None:
            try:
                pct = float(diff_percentage)
                if pct < 0.15:
                    raise SkipEvent(
                        f"Diff {pct:.0%} — minor copy edit, no GTM implication"
                    )
            except (TypeError, ValueError):
                pass

        # ── Skip rule 6: low significance ────────────────────────
        if isinstance(change_significance, str):
            if change_significance.lower() not in ("high", "medium"):
                raise SkipEvent(
                    f"Significance={change_significance} — below threshold"
                )

        # ── Skip rule 7: no GTM keywords → no outbound signal ───
        matches = _match_gtm_keywords(extracted_keywords)
        if not matches:
            raise SkipEvent("No GTM-relevant keywords — fails salesperson outbound test")

        # ── Determine shift type ─────────────────────────────────
        shift_type = _dominant_shift_type(matches, page_type=page_type)
        if not shift_type:
            raise SkipEvent("Could not determine shift type")

        # ── Quality gate: salesperson outbound test ──────────────
        # Compliance-only signals without ICP or GTM shift don't pass.
        categories = {cat for _, cat in matches}
        if categories == {"compliance"}:
            raise SkipEvent(
                "Compliance update only — no ICP or GTM shift detected"
            )

        # ── Build signal ─────────────────────────────────────────
        title = _build_title(
            shift_type, page_type, matches, previous_text, current_text,
        )
        interpretation = _build_interpretation(
            shift_type, page_type, matches, previous_text, current_text,
        )

        occurred_at = event.occurred_at or event.fetched_at

        return NormalizedSignal(
            signal_type="positioning_shift",
            title=title,
            summary=interpretation,
            occurred_at=occurred_at,
        )
