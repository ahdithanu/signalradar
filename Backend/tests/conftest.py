"""Shared test fixtures — isolated test database using transactions.

Each test runs inside a transaction that is rolled back after the test,
so tests never pollute each other.
"""

import uuid
from datetime import datetime, timezone, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.db import Base, get_db
from app.main import app
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.models.account import Account
from app.models.signal import Signal
from app.models.account_source import AccountSource
from app.models.raw_event import RawEvent


# Use the same DB but with isolated transactions per test.
# For CI you could point to a separate test DB via TEST_DATABASE_URL.
TEST_DATABASE_URL = settings.database_url

engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)


@pytest.fixture()
def db_session():
    """Yield a Session wrapped in a transaction that gets rolled back."""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    # Make session.begin_nested() work inside the outer transaction
    nested = connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(session, transaction_obj):
        nonlocal nested
        if transaction_obj.nested and not transaction_obj._parent.nested:
            nested = connection.begin_nested()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db_session):
    """TestClient with the db dependency overridden to use the test session."""
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ── Helper factories ────────────────────────────────────────────────────

def _utcnow():
    return datetime.now(timezone.utc)


@pytest.fixture()
def workspace_a(db_session):
    """Create workspace A with an owner user."""
    user = User(id=uuid.uuid4(), email="user_a@test.com", display_name="User A")
    db_session.add(user)
    db_session.flush()

    ws = Workspace(id=uuid.uuid4(), name="Workspace A", created_by=user.id)
    db_session.add(ws)
    db_session.flush()

    db_session.add(WorkspaceMember(user_id=user.id, workspace_id=ws.id, role="owner"))
    db_session.flush()

    return {"user": user, "workspace": ws}


@pytest.fixture()
def workspace_b(db_session):
    """Create workspace B with a different owner user."""
    user = User(id=uuid.uuid4(), email="user_b@test.com", display_name="User B")
    db_session.add(user)
    db_session.flush()

    ws = Workspace(id=uuid.uuid4(), name="Workspace B", created_by=user.id)
    db_session.add(ws)
    db_session.flush()

    db_session.add(WorkspaceMember(user_id=user.id, workspace_id=ws.id, role="owner"))
    db_session.flush()

    return {"user": user, "workspace": ws}


@pytest.fixture()
def account_in_a(db_session, workspace_a):
    """Create an account in workspace A."""
    acct = Account(
        id=uuid.uuid4(),
        workspace_id=workspace_a["workspace"].id,
        name="Acme Corp (A)",
        domain="acme-a.com",
        industry="SaaS",
        status="New",
    )
    db_session.add(acct)
    db_session.flush()
    return acct


@pytest.fixture()
def account_in_b(db_session, workspace_b):
    """Create an account in workspace B."""
    acct = Account(
        id=uuid.uuid4(),
        workspace_id=workspace_b["workspace"].id,
        name="Beta Inc (B)",
        domain="beta-b.com",
        industry="Fintech",
        status="New",
    )
    db_session.add(acct)
    db_session.flush()
    return acct


@pytest.fixture()
def signal_in_a(db_session, account_in_a):
    """Create a signal in workspace A."""
    sig = Signal(
        id=uuid.uuid4(),
        workspace_id=account_in_a.workspace_id,
        account_id=account_in_a.id,
        type="funding",
        title="Raised $10M Series A",
        summary="Growth signal.",
        occurred_at=_utcnow() - timedelta(days=5),
    )
    db_session.add(sig)
    db_session.flush()
    return sig


@pytest.fixture()
def signal_in_b(db_session, account_in_b):
    """Create a signal in workspace B."""
    sig = Signal(
        id=uuid.uuid4(),
        workspace_id=account_in_b.workspace_id,
        account_id=account_in_b.id,
        type="hiring",
        title="Hiring VP Sales",
        summary="Expansion signal.",
        occurred_at=_utcnow() - timedelta(days=3),
    )
    db_session.add(sig)
    db_session.flush()
    return sig
