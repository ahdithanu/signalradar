import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.account import Account
SEED_ACCOUNTS = [
    {
        "id": uuid.UUID("00000000-0000-0000-0000-000000000001"),
        "name": "Acme Corp",
        "domain": "acme.com",
        "industry": "SaaS",
        "employee_count": 420,
        "location": "San Francisco, CA",
        "description": "Cloud automation platform for enterprise sales teams.",
    },
    {
        "id": uuid.UUID("00000000-0000-0000-0000-000000000002"),
        "name": "Globex Industries",
        "domain": "globex.io",
        "industry": "Manufacturing",
        "employee_count": 1800,
        "location": "Chicago, IL",
        "description": "Industrial IoT and supply chain analytics.",
    },
    {
        "id": uuid.UUID("00000000-0000-0000-0000-000000000003"),
        "name": "Initech Solutions",
        "domain": "initech.com",
        "industry": "FinTech",
        "employee_count": 310,
        "location": "Austin, TX",
        "description": "Compliance and risk management software for mid-market banks.",
    },
    {
        "id": uuid.UUID("00000000-0000-0000-0000-000000000004"),
        "name": "Umbrella Analytics",
        "domain": "umbrella.ai",
        "industry": "SaaS",
        "employee_count": 95,
        "location": "New York, NY",
        "description": "AI-powered data observability for data-driven revenue teams.",
    },
    {
        "id": uuid.UUID("00000000-0000-0000-0000-000000000005"),
        "name": "Stark Dynamics",
        "domain": "starkdynamics.com",
        "industry": "Defense Tech",
        "employee_count": 670,
        "location": "Boston, MA",
        "description": "Next-gen aerospace and cyber defense solutions.",
    },
]
def seed_accounts(db: Session) -> int:
    """Insert seed accounts if they do not already exist. Returns count inserted."""
    inserted = 0
    for data in SEED_ACCOUNTS:
        existing = db.get(Account, data["id"])
        if existing is None:
            account = Account(**data)
            db.add(account)
            inserted += 1
    db.commit()
    return inserted
