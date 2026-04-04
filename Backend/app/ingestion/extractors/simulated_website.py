"""Simulated website diff extractor for local testing.

Produces realistic website change events for the 8 seed accounts.
Only STRONG signals that indicate real ICP, GTM motion, or positioning
changes — plus intentional noise events to exercise skip rules.

Each event represents a diff between two snapshots of a company webpage.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta

from app.models.account_source import AccountSource
from app.ingestion.extractors.base import ExtractedEvent

logger = logging.getLogger(__name__)


def _days_ago(n: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=n)


# ---------------------------------------------------------------------------
# Simulated diffs grouped by account slug.
#
# SIGNAL DESIGN PRINCIPLE: Every strong event must answer:
#   "Would a salesperson change their outreach because of this?"
#
# Strong events:
#   - SMB → enterprise ICP shift
#   - PLG self-serve → sales-assisted motion shift
#   - New vertical landing page (healthcare, fintech, etc.)
#   - Pricing restructure toward enterprise / contact-sales
#   - "Tool" → "Platform" messaging evolution
#
# Noise events (MUST be skipped by normalizer):
#   - Blog posts, legal updates, footer changes
#   - Minor copy edits (<10% diff)
#   - Generic product updates with no GTM implication
#   - Empty or missing content
# ---------------------------------------------------------------------------

_SIMULATED_DIFFS: dict[str, list[dict]] = {

    # ── Nova Payments ─────────────────────────────────────────────
    # Signal: Homepage rewrote from SMB self-serve → enterprise sales-led
    "nova-payments": [
        {
            "diff_id": "web-diff-nova-001",
            "page_url": "https://novapayments.io",
            "page_type": "homepage",
            "previous_text": "The simplest way to accept payments for small businesses. Start free today — no credit card required.",
            "current_text": "Enterprise-grade payment infrastructure built for high-growth companies. PCI DSS Level 1 certified. SOC 2 compliant. Talk to our payments team.",
            "changed_sections": ["hero", "trust_badges", "cta"],
            "extracted_keywords": ["enterprise", "high-growth", "PCI DSS", "SOC 2", "talk to our payments team"],
            "change_significance": "high",
            "diff_percentage": 0.61,
            "detected_shift": "icp_upmarket",
        },
        # NOISE: terms of service version bump
        {
            "diff_id": "web-diff-nova-002",
            "page_url": "https://novapayments.io/legal/terms",
            "page_type": "legal",
            "previous_text": "Terms of Service v2.1 — effective January 2026",
            "current_text": "Terms of Service v2.2 — effective March 2026",
            "changed_sections": ["footer"],
            "extracted_keywords": ["terms"],
            "change_significance": "low",
            "diff_percentage": 0.02,
        },
    ],

    # ── Ramp AI ───────────────────────────────────────────────────
    # Signal: Brand-new financial services vertical page
    "ramp-ai": [
        {
            "diff_id": "web-diff-ramp-001",
            "page_url": "https://rampai.com/solutions/financial-services",
            "page_type": "use_case",
            "previous_text": None,
            "current_text": "AI-powered automation for financial services. Built for compliance teams at banks, insurers, and fintechs. Reduce manual review by 80%. Schedule a consultation with our financial services team.",
            "changed_sections": ["new_page"],
            "extracted_keywords": ["financial services", "compliance", "banks", "fintech", "schedule a consultation"],
            "change_significance": "high",
            "diff_percentage": 1.0,
            "detected_shift": "new_vertical",
        },
        # NOISE: generic blog post
        {
            "diff_id": "web-diff-ramp-003",
            "page_url": "https://rampai.com/blog/ai-trends-2026",
            "page_type": "blog",
            "previous_text": None,
            "current_text": "5 AI trends to watch in 2026",
            "changed_sections": ["blog_listing"],
            "extracted_keywords": ["AI", "trends"],
            "change_significance": "low",
            "diff_percentage": 0.03,
        },
    ],

    # ── Vector Labs ───────────────────────────────────────────────
    # Signal: Pricing page killed self-serve enterprise tier, added "Contact Sales"
    "vector-labs": [
        {
            "diff_id": "web-diff-vector-001",
            "page_url": "https://vectorlabs.dev/pricing",
            "page_type": "pricing",
            "previous_text": "Free: unlimited API calls. Pro: $49/mo. Enterprise: $199/mo. All plans are self-serve. No sales calls needed.",
            "current_text": "Free: 1,000 API calls/mo. Pro: $99/mo (up to 10 seats). Enterprise: Contact sales for custom pricing. Volume discounts for teams over 50.",
            "changed_sections": ["pricing_tiers", "cta", "faq"],
            "extracted_keywords": ["contact sales", "custom pricing", "enterprise", "volume discounts", "teams over 50"],
            "change_significance": "high",
            "diff_percentage": 0.42,
            "detected_shift": "gtm_sales_led",
        },
        # NOISE: blog post — no GTM signal
        {
            "diff_id": "web-diff-vector-002",
            "page_url": "https://vectorlabs.dev/blog/api-performance-tips",
            "page_type": "blog",
            "previous_text": None,
            "current_text": "10 tips for better API performance in production",
            "changed_sections": ["blog_listing"],
            "extracted_keywords": ["API", "performance", "tips"],
            "change_significance": "low",
            "diff_percentage": 0.04,
        },
    ],

    # ── Cobalt Health ─────────────────────────────────────────────
    # Signal: New enterprise use-case page for hospital systems
    "cobalt-health": [
        {
            "diff_id": "web-diff-cobalt-001",
            "page_url": "https://cobalthealth.co/solutions/hospital-systems",
            "page_type": "use_case",
            "previous_text": None,
            "current_text": "Purpose-built for multi-site hospital networks. Unified patient flow, cross-facility staff scheduling, and HIPAA-compliant analytics. Request an enterprise pilot for your health system.",
            "changed_sections": ["new_page"],
            "extracted_keywords": ["hospital systems", "multi-site", "enterprise pilot", "HIPAA", "health system"],
            "change_significance": "high",
            "diff_percentage": 1.0,
            "detected_shift": "new_vertical",
        },
    ],

    # ── Prism Analytics ───────────────────────────────────────────
    # Signal: Homepage shifted from individual users to team/org positioning
    "prism-analytics": [
        {
            "diff_id": "web-diff-prism-001",
            "page_url": "https://prismanalytics.io",
            "page_type": "homepage",
            "previous_text": "Analytics for the data-curious individual. Sign up free and start exploring your data today.",
            "current_text": "The analytics platform for data teams. Collaborate across your organization with shared dashboards, governed metrics, and role-based access. Start a team trial.",
            "changed_sections": ["hero", "value_props", "cta"],
            "extracted_keywords": ["data teams", "collaborate", "organization", "governed metrics", "role-based access", "team trial"],
            "change_significance": "high",
            "diff_percentage": 0.55,
            "detected_shift": "icp_upmarket",
        },
        # NOISE: empty diff — about page unchanged
        {
            "diff_id": "web-diff-prism-002",
            "page_url": "https://prismanalytics.io/about",
            "page_type": "about",
            "previous_text": "About us — we make analytics simple",
            "current_text": "About us — we make analytics simple",
            "changed_sections": [],
            "extracted_keywords": [],
            "change_significance": "low",
            "diff_percentage": 0.0,
        },
    ],

    # ── Meridian Logistics ────────────────────────────────────────
    # Signal: New geographic market expansion page (EMEA)
    "meridian-logistics": [
        {
            "diff_id": "web-diff-meridian-001",
            "page_url": "https://meridianlogistics.com/markets/europe",
            "page_type": "use_case",
            "previous_text": None,
            "current_text": "Meridian now serves European logistics. Cross-border shipping, customs automation, and regional warehousing across 12 EU countries. Contact our EMEA sales team for a regional assessment.",
            "changed_sections": ["new_page"],
            "extracted_keywords": ["Europe", "EMEA", "cross-border", "customs automation", "EMEA sales team"],
            "change_significance": "high",
            "diff_percentage": 1.0,
            "detected_shift": "new_market",
        },
        # NOISE: status page — no GTM signal
        {
            "diff_id": "web-diff-meridian-002",
            "page_url": "https://meridianlogistics.com/status",
            "page_type": "status",
            "previous_text": "All systems operational",
            "current_text": "All systems operational — last checked 5 min ago",
            "changed_sections": ["status_banner"],
            "extracted_keywords": [],
            "change_significance": "low",
            "diff_percentage": 0.01,
        },
    ],

    # ── Athena Security ───────────────────────────────────────────
    # Signal: Full homepage rebrand from "simple tool" → "enterprise platform"
    "athena-security": [
        {
            "diff_id": "web-diff-athena-001",
            "page_url": "https://athenasecurity.io",
            "page_type": "homepage",
            "previous_text": "Simple security tools for small teams. Get started in minutes — no expertise required.",
            "current_text": "The enterprise security platform for regulated industries. SOC 2 Type II. FedRAMP authorized. HIPAA compliant. Talk to a security advisor about your compliance needs.",
            "changed_sections": ["hero", "trust_badges", "compliance_section", "cta"],
            "extracted_keywords": ["enterprise", "platform", "regulated industries", "SOC 2", "FedRAMP", "HIPAA", "security advisor", "compliance"],
            "change_significance": "high",
            "diff_percentage": 0.68,
            "detected_shift": "icp_upmarket",
        },
    ],

    # ── Flux Commerce ─────────────────────────────────────────────
    # Signal: Pricing added enterprise tier + annual-only + contact sales
    "flux-commerce": [
        {
            "diff_id": "web-diff-flux-001",
            "page_url": "https://fluxcommerce.co/pricing",
            "page_type": "pricing",
            "previous_text": "Starter: $29/mo. Growth: $99/mo. All plans month-to-month, cancel anytime. No enterprise tier — we believe in simplicity.",
            "current_text": "Starter: $25/mo billed annually. Growth: $79/mo billed annually. Enterprise: custom pricing — contact sales. Includes dedicated account manager, SLA, and priority support.",
            "changed_sections": ["pricing_tiers", "enterprise_section", "cta"],
            "extracted_keywords": ["enterprise", "custom pricing", "contact sales", "dedicated account manager", "SLA"],
            "change_significance": "high",
            "diff_percentage": 0.47,
            "detected_shift": "gtm_sales_led",
        },
        # NOISE: hyphen fix — trivial copy edit
        {
            "diff_id": "web-diff-flux-002",
            "page_url": "https://fluxcommerce.co",
            "page_type": "homepage",
            "previous_text": "The best ecommerce platform for growing brands.",
            "current_text": "The best e-commerce platform for growing brands.",
            "changed_sections": ["hero"],
            "extracted_keywords": [],
            "change_significance": "low",
            "diff_percentage": 0.01,
        },
    ],
}


class SimulatedWebsiteExtractor:
    """Returns pre-built website diff events for local testing.

    Includes noise events to verify the normalizer skips them.
    """

    def extract(self, source: AccountSource) -> list[ExtractedEvent]:
        slug = source.source_key
        if not slug:
            return []

        diffs = _SIMULATED_DIFFS.get(slug)
        if not diffs:
            logger.info("No simulated website diffs for slug=%s", slug)
            return []

        events: list[ExtractedEvent] = []
        for i, diff in enumerate(diffs):
            occurred = _days_ago(3 + 5 * i)

            payload = {
                "page_url": diff.get("page_url"),
                "page_type": diff.get("page_type"),
                "previous_text": diff.get("previous_text"),
                "current_text": diff.get("current_text"),
                "changed_sections": diff.get("changed_sections"),
                "extracted_keywords": diff.get("extracted_keywords"),
                "change_significance": diff.get("change_significance"),
                "diff_percentage": diff.get("diff_percentage"),
                "detected_shift": diff.get("detected_shift"),
                "source": "simulated_website_diff",
            }

            diff_id = diff.get("diff_id")
            external_id = f"webdiff:{diff_id}" if diff_id else None

            events.append(
                ExtractedEvent(
                    account_source_id=source.id,
                    account_id=source.account_id,
                    event_type="website_change",
                    raw_payload=payload,
                    source_url=diff.get("page_url"),
                    external_id=external_id,
                    occurred_at=occurred,
                )
            )

        logger.info(
            "Simulated website extractor: %d events for %s",
            len(events),
            slug,
        )
        return events
