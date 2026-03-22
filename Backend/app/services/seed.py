import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.models.account import Account
from app.models.signal import Signal
from app.models.account_source import AccountSource
from app.auth import DEFAULT_USER_ID, DEFAULT_WORKSPACE_ID


def _d(days_ago: int) -> datetime:
    """Return a UTC datetime `days_ago` days in the past."""
    return datetime.now(timezone.utc) - timedelta(days=days_ago)


# Default dev user and workspace IDs
_WS_ID = DEFAULT_WORKSPACE_ID


def seed_dev_context(db: Session) -> int:
    """Create default dev user + workspace if they don't exist.
    Must run BEFORE seed_accounts.
    """
    created = 0
    user = db.get(User, DEFAULT_USER_ID)
    if user is None:
        user = User(id=DEFAULT_USER_ID, email="dev@signalradar.local", display_name="Dev User")
        db.add(user)
        db.flush()
        created += 1

    workspace = db.get(Workspace, DEFAULT_WORKSPACE_ID)
    if workspace is None:
        workspace = Workspace(id=DEFAULT_WORKSPACE_ID, name="Dev Workspace", created_by=user.id)
        db.add(workspace)
        db.flush()
        created += 1

    from sqlalchemy import select
    membership = db.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.user_id == DEFAULT_USER_ID,
            WorkspaceMember.workspace_id == DEFAULT_WORKSPACE_ID,
        )
    )
    if membership is None:
        db.add(WorkspaceMember(
            user_id=DEFAULT_USER_ID,
            workspace_id=DEFAULT_WORKSPACE_ID,
            role="owner",
        ))
        created += 1

    db.commit()
    return created


SEED_ACCOUNTS = [
    {
        "id": uuid.UUID("00000000-0000-0000-0000-000000000001"),
        "workspace_id": _WS_ID,
        "name": "Nova Payments",
        "domain": "novapayments.io",
        "industry": "Fintech",
        "employee_count": 85,
        "funding_stage": "Series A",
        "status": "New",
        "why_now": "Recently raised Series A funding and is building out its sales organization, suggesting a need for improved pipeline generation and revenue infrastructure.",
        "recommended_buyer_persona": ["Head of Sales", "VP Revenue", "Revenue Operations Lead"],
        "suggested_outreach_angle": "Scaling go-to-market infrastructure after funding and hiring new sales roles.",
        "strategic_intelligence": {
            "strategicTheme": "Payments infrastructure expansion",
            "managementTone": "Confident but efficiency-focused",
            "commercialPressureScore": "medium",
            "narrativeShift": "Increasing emphasis on enterprise sales motion",
            "suggestedGTMRelevance": "Tools that accelerate revenue growth without increasing headcount significantly.",
        },
        "signals": [
            {"type": "funding", "title": "Raised $18M Series A", "summary": "Entering rapid scaling phase and likely expanding GTM team.", "days_ago": 45},
            {"type": "hiring", "title": "Hiring 3 Sales Development Representatives", "summary": "Expanding outbound pipeline generation.", "days_ago": 28},
            {"type": "hiring", "title": "Hiring Revenue Operations Manager", "summary": "Investing in revenue infrastructure and sales systems.", "days_ago": 23},
        ],
    },
    {
        "id": uuid.UUID("00000000-0000-0000-0000-000000000002"),
        "workspace_id": _WS_ID,
        "name": "Ramp AI",
        "domain": "rampai.com",
        "industry": "AI / ML",
        "employee_count": 42,
        "funding_stage": "Series A",
        "status": "Reviewing",
        "why_now": "Just closed Series A and is actively hiring growth leadership, indicating readiness to invest in scalable acquisition channels.",
        "recommended_buyer_persona": ["Head of Growth", "CEO", "VP Marketing"],
        "suggested_outreach_angle": "Building scalable growth engine post-funding with new growth leadership.",
        "strategic_intelligence": {
            "strategicTheme": "AI-powered automation",
            "managementTone": "Aggressive growth-oriented",
            "commercialPressureScore": "high",
            "narrativeShift": "Shifting from product-led to sales-assisted growth",
            "suggestedGTMRelevance": "Tools that bridge PLG with outbound sales motions.",
        },
        "signals": [
            {"type": "funding", "title": "Raised $12M Series A funding", "summary": "Entering rapid scaling phase and likely expanding GTM team.", "days_ago": 42},
            {"type": "hiring", "title": "Hiring Head of Growth", "summary": "Prioritizing growth and customer acquisition.", "days_ago": 18},
            {"type": "positioning_shift", "title": "Pivoting ICP from SMB self-serve to mid-market sales-assisted", "summary": "Shifting target customer from PLG self-serve users to mid-market accounts requiring sales engagement. Indicates new outbound motion.", "days_ago": 8},
        ],
    },
    {
        "id": uuid.UUID("00000000-0000-0000-0000-000000000003"),
        "workspace_id": _WS_ID,
        "name": "Vector Labs",
        "domain": "vectorlabs.dev",
        "industry": "Developer Tools",
        "employee_count": 120,
        "funding_stage": "Series B",
        "status": "New",
        "why_now": "Rapid revenue growth and enterprise launch signal a transition to a more structured GTM motion requiring new tooling.",
        "recommended_buyer_persona": ["Revenue Operations Lead", "Head of Sales", "VP Engineering"],
        "suggested_outreach_angle": "Supporting enterprise go-to-market transition with scalable revenue operations.",
        "strategic_intelligence": {
            "strategicTheme": "Enterprise expansion",
            "managementTone": "Measured and strategic",
            "commercialPressureScore": "medium",
            "narrativeShift": "From developer community to enterprise sales",
            "suggestedGTMRelevance": "Enterprise sales enablement and CRM infrastructure.",
        },
        "signals": [
            {"type": "hiring", "title": "Hiring Revenue Operations Manager", "summary": "Investing in revenue infrastructure and sales systems.", "days_ago": 33},
            {"type": "growth", "title": "Revenue grew 140% YoY", "summary": "Rapid growth likely straining existing GTM processes.", "days_ago": 59},
            {"type": "product_launch", "title": "Launched enterprise tier", "summary": "Moving upmarket requires new sales infrastructure.", "days_ago": 15},
        ],
    },
    {
        "id": uuid.UUID("00000000-0000-0000-0000-000000000004"),
        "workspace_id": _WS_ID,
        "name": "Cobalt Health",
        "domain": "cobalthealth.co",
        "industry": "Healthcare Tech",
        "employee_count": 200,
        "funding_stage": "Series B",
        "status": "New",
        "why_now": "Hiring senior sales leadership while experiencing rapid customer growth signals readiness for structured outbound.",
        "recommended_buyer_persona": ["VP of Sales", "Head of Business Development"],
        "suggested_outreach_angle": "Enabling sales team scaling during rapid customer acquisition phase.",
        "strategic_intelligence": {
            "strategicTheme": "Healthcare digitization",
            "managementTone": "Optimistic with urgency",
            "commercialPressureScore": "high",
            "narrativeShift": "Accelerating from pilot programs to full deployment",
            "suggestedGTMRelevance": "Tools for managing complex enterprise sales cycles in healthcare.",
        },
        "signals": [
            {"type": "hiring", "title": "Hiring VP of Sales", "summary": "Building senior sales leadership for aggressive expansion.", "days_ago": 14},
            {"type": "growth", "title": "Customer base grew 90% in Q4", "summary": "Strong product-market fit driving commercial pressure.", "days_ago": 54},
            {"type": "positioning_shift", "title": "Repositioning from clinic-focused to hospital system enterprise sales", "summary": "Expanding ICP from small clinics to large hospital networks. Requires enterprise sales infrastructure and longer deal cycles.", "days_ago": 11},
        ],
    },
    {
        "id": uuid.UUID("00000000-0000-0000-0000-000000000005"),
        "workspace_id": _WS_ID,
        "name": "Prism Analytics",
        "domain": "prismanalytics.io",
        "industry": "Data Analytics",
        "employee_count": 55,
        "funding_stage": "Seed",
        "status": "Reviewing",
        "why_now": "Transitioning from founder-led sales to a dedicated sales team, creating demand for sales tooling and processes.",
        "recommended_buyer_persona": ["CEO", "Head of Sales", "Founding Team"],
        "suggested_outreach_angle": "Helping build the first sales stack as they transition from founder-led to team-based selling.",
        "strategic_intelligence": {
            "strategicTheme": "Data democratization",
            "managementTone": "Experimental and lean",
            "commercialPressureScore": "low",
            "narrativeShift": "Moving from technical product to commercial readiness",
            "suggestedGTMRelevance": "Lightweight sales tools suited for early-stage teams.",
        },
        "signals": [
            {"type": "funding", "title": "Closed $5M seed round", "summary": "Early-stage company beginning to build GTM function.", "days_ago": 25},
            {"type": "hiring", "title": "Hiring first Account Executive", "summary": "Transitioning from founder-led sales to dedicated sales team.", "days_ago": 10},
        ],
    },
    {
        "id": uuid.UUID("00000000-0000-0000-0000-000000000006"),
        "workspace_id": _WS_ID,
        "name": "Meridian Logistics",
        "domain": "meridianlogistics.com",
        "industry": "Supply Chain",
        "employee_count": 310,
        "funding_stage": "Series C",
        "status": "New",
        "why_now": "Geographic expansion and regional sales hiring indicate a need for scalable outbound infrastructure across multiple markets.",
        "recommended_buyer_persona": ["VP Sales", "Head of Revenue", "Regional Sales Director"],
        "suggested_outreach_angle": "Supporting multi-market GTM expansion with unified sales infrastructure.",
        "strategic_intelligence": {
            "strategicTheme": "Supply chain modernization",
            "managementTone": "Methodical and growth-focused",
            "commercialPressureScore": "medium",
            "narrativeShift": "From domestic leader to international expansion",
            "suggestedGTMRelevance": "Multi-region sales coordination and pipeline management tools.",
        },
        "signals": [
            {"type": "growth", "title": "Expanded to 3 new markets", "summary": "Geographic expansion creates new GTM requirements.", "days_ago": 44},
            {"type": "hiring", "title": "Hiring Regional Sales Directors", "summary": "Building regional sales capacity for market expansion.", "days_ago": 21},
        ],
    },
    {
        "id": uuid.UUID("00000000-0000-0000-0000-000000000007"),
        "workspace_id": _WS_ID,
        "name": "Athena Security",
        "domain": "athenasecurity.io",
        "industry": "Cybersecurity",
        "employee_count": 150,
        "funding_stage": "Series B",
        "status": "Dismissed",
        "why_now": "New product launch paired with enterprise AE hiring signals a new sales motion requiring outbound support.",
        "recommended_buyer_persona": ["VP Sales", "Head of Enterprise Sales"],
        "suggested_outreach_angle": "Accelerating enterprise pipeline for newly launched compliance product.",
        "strategic_intelligence": {
            "strategicTheme": "Compliance automation",
            "managementTone": "Cautiously optimistic",
            "commercialPressureScore": "medium",
            "narrativeShift": "Adding compliance layer to core security offering",
            "suggestedGTMRelevance": "Enterprise sales tools for regulated industry verticals.",
        },
        "signals": [
            {"type": "product_launch", "title": "Launched compliance automation suite", "summary": "New product line requires dedicated sales motion.", "days_ago": 31},
            {"type": "hiring", "title": "Hiring 2 Enterprise AEs", "summary": "Building enterprise sales capacity.", "days_ago": 13},
        ],
    },
    {
        "id": uuid.UUID("00000000-0000-0000-0000-000000000008"),
        "workspace_id": _WS_ID,
        "name": "Flux Commerce",
        "domain": "fluxcommerce.co",
        "industry": "E-commerce",
        "employee_count": 95,
        "funding_stage": "Series A",
        "status": "Ready for Outreach",
        "why_now": "Fresh funding with a lean team suggests they'll be building out GTM capabilities soon.",
        "recommended_buyer_persona": ["CEO", "Head of Growth"],
        "suggested_outreach_angle": "Building GTM foundation post-Series A for rapid market capture.",
        "strategic_intelligence": {
            "strategicTheme": "Commerce platform expansion",
            "managementTone": "Ambitious and fast-moving",
            "commercialPressureScore": "high",
            "narrativeShift": "From niche player to broad commerce platform",
            "suggestedGTMRelevance": "Growth tools for scaling customer acquisition post-funding.",
        },
        "signals": [
            {"type": "funding", "title": "Raised $10M Series A", "summary": "Post-funding expansion phase beginning.", "days_ago": 38},
        ],
    },
]


# Crunchbase sources for each account.
SEED_ACCOUNT_SOURCES = [
    {
        "id": uuid.UUID("10000000-0000-0000-0000-000000000001"),
        "workspace_id": _WS_ID,
        "account_id": uuid.UUID("00000000-0000-0000-0000-000000000001"),
        "source_type": "crunchbase",
        "source_url": "https://www.crunchbase.com/organization/nova-payments",
        "source_key": "nova-payments",
    },
    {
        "id": uuid.UUID("10000000-0000-0000-0000-000000000002"),
        "workspace_id": _WS_ID,
        "account_id": uuid.UUID("00000000-0000-0000-0000-000000000002"),
        "source_type": "crunchbase",
        "source_url": "https://www.crunchbase.com/organization/ramp-ai",
        "source_key": "ramp-ai",
    },
    {
        "id": uuid.UUID("10000000-0000-0000-0000-000000000003"),
        "workspace_id": _WS_ID,
        "account_id": uuid.UUID("00000000-0000-0000-0000-000000000003"),
        "source_type": "crunchbase",
        "source_url": "https://www.crunchbase.com/organization/vector-labs",
        "source_key": "vector-labs",
    },
    {
        "id": uuid.UUID("10000000-0000-0000-0000-000000000004"),
        "workspace_id": _WS_ID,
        "account_id": uuid.UUID("00000000-0000-0000-0000-000000000004"),
        "source_type": "crunchbase",
        "source_url": "https://www.crunchbase.com/organization/cobalt-health",
        "source_key": "cobalt-health",
    },
    {
        "id": uuid.UUID("10000000-0000-0000-0000-000000000005"),
        "workspace_id": _WS_ID,
        "account_id": uuid.UUID("00000000-0000-0000-0000-000000000005"),
        "source_type": "crunchbase",
        "source_url": "https://www.crunchbase.com/organization/prism-analytics",
        "source_key": "prism-analytics",
    },
    {
        "id": uuid.UUID("10000000-0000-0000-0000-000000000006"),
        "workspace_id": _WS_ID,
        "account_id": uuid.UUID("00000000-0000-0000-0000-000000000006"),
        "source_type": "crunchbase",
        "source_url": "https://www.crunchbase.com/organization/meridian-logistics",
        "source_key": "meridian-logistics",
    },
    {
        "id": uuid.UUID("10000000-0000-0000-0000-000000000007"),
        "workspace_id": _WS_ID,
        "account_id": uuid.UUID("00000000-0000-0000-0000-000000000007"),
        "source_type": "crunchbase",
        "source_url": "https://www.crunchbase.com/organization/athena-security",
        "source_key": "athena-security",
    },
    {
        "id": uuid.UUID("10000000-0000-0000-0000-000000000008"),
        "workspace_id": _WS_ID,
        "account_id": uuid.UUID("00000000-0000-0000-0000-000000000008"),
        "source_type": "crunchbase",
        "source_url": "https://www.crunchbase.com/organization/flux-commerce",
        "source_key": "flux-commerce",
    },
]


def seed_accounts(db: Session) -> int:
    """Insert seed accounts and signals if they do not already exist."""
    inserted = 0
    for data in SEED_ACCOUNTS:
        existing = db.get(Account, data["id"])
        if existing is not None:
            continue
        signals_data = data.pop("signals")
        account = Account(**data)
        db.add(account)
        db.flush()
        for sig in signals_data:
            signal = Signal(
                workspace_id=_WS_ID,
                account_id=account.id,
                type=sig["type"],
                title=sig["title"],
                summary=sig["summary"],
                occurred_at=_d(sig["days_ago"]),
            )
            db.add(signal)
        inserted += 1
    db.commit()
    return inserted


SEED_WEBSITE_SOURCES = [
    {
        "id": uuid.UUID("20000000-0000-0000-0000-000000000001"),
        "workspace_id": _WS_ID,
        "account_id": uuid.UUID("00000000-0000-0000-0000-000000000001"),
        "source_type": "website",
        "source_url": "https://novapayments.io",
        "source_key": "nova-payments",
    },
    {
        "id": uuid.UUID("20000000-0000-0000-0000-000000000002"),
        "workspace_id": _WS_ID,
        "account_id": uuid.UUID("00000000-0000-0000-0000-000000000002"),
        "source_type": "website",
        "source_url": "https://rampai.com",
        "source_key": "ramp-ai",
    },
    {
        "id": uuid.UUID("20000000-0000-0000-0000-000000000003"),
        "workspace_id": _WS_ID,
        "account_id": uuid.UUID("00000000-0000-0000-0000-000000000003"),
        "source_type": "website",
        "source_url": "https://vectorlabs.dev",
        "source_key": "vector-labs",
    },
    {
        "id": uuid.UUID("20000000-0000-0000-0000-000000000004"),
        "workspace_id": _WS_ID,
        "account_id": uuid.UUID("00000000-0000-0000-0000-000000000004"),
        "source_type": "website",
        "source_url": "https://cobalthealth.co",
        "source_key": "cobalt-health",
    },
    {
        "id": uuid.UUID("20000000-0000-0000-0000-000000000005"),
        "workspace_id": _WS_ID,
        "account_id": uuid.UUID("00000000-0000-0000-0000-000000000005"),
        "source_type": "website",
        "source_url": "https://prismanalytics.io",
        "source_key": "prism-analytics",
    },
    {
        "id": uuid.UUID("20000000-0000-0000-0000-000000000006"),
        "workspace_id": _WS_ID,
        "account_id": uuid.UUID("00000000-0000-0000-0000-000000000006"),
        "source_type": "website",
        "source_url": "https://meridianlogistics.com",
        "source_key": "meridian-logistics",
    },
    {
        "id": uuid.UUID("20000000-0000-0000-0000-000000000007"),
        "workspace_id": _WS_ID,
        "account_id": uuid.UUID("00000000-0000-0000-0000-000000000007"),
        "source_type": "website",
        "source_url": "https://athenasecurity.io",
        "source_key": "athena-security",
    },
    {
        "id": uuid.UUID("20000000-0000-0000-0000-000000000008"),
        "workspace_id": _WS_ID,
        "account_id": uuid.UUID("00000000-0000-0000-0000-000000000008"),
        "source_type": "website",
        "source_url": "https://fluxcommerce.co",
        "source_key": "flux-commerce",
    },
]


def seed_account_sources(db: Session) -> int:
    """Insert seed account_sources if they do not already exist."""
    inserted = 0
    all_sources = SEED_ACCOUNT_SOURCES + SEED_WEBSITE_SOURCES
    for data in all_sources:
        existing = db.get(AccountSource, data["id"])
        if existing is not None:
            continue
        source = AccountSource(**data)
        db.add(source)
        inserted += 1
    db.commit()
    return inserted
