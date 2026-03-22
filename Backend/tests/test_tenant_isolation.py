"""Task 5 — Tenant isolation tests.

Verifies that workspace-scoped queries never leak data across tenants.
Tests cover: accounts, signals, and evidence endpoints.
"""

import uuid
from datetime import datetime, timezone, timedelta

from app.auth import WorkspaceContext, get_workspace_context
from app.db import get_db
from app.main import app
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.models.account import Account
from app.models.signal import Signal
from app.models.raw_event import RawEvent
from app.models.account_source import AccountSource


def _make_dev_context(db_session, workspace_id, user):
    """Build a WorkspaceContext for dependency override."""
    return WorkspaceContext(
        user=user,
        workspace_id=workspace_id,
        role="owner",
        db=db_session,
    )


def _setup_overrides(db_session, workspace):
    """Set app dependency overrides for a given workspace context."""
    def override_db():
        yield db_session

    def override_ctx():
        return _make_dev_context(
            db_session, workspace["workspace"].id, workspace["user"]
        )

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_workspace_context] = override_ctx


def _clear_overrides():
    app.dependency_overrides.clear()


# ── Accounts isolation ──────────────────────────────────────────────────

class TestAccountIsolation:
    def test_list_accounts_only_returns_own_workspace(
        self, client, db_session, workspace_a, workspace_b, account_in_a, account_in_b
    ):
        """Listing accounts in workspace A must not include workspace B accounts."""
        _setup_overrides(db_session, workspace_a)

        resp = client.get("/accounts")
        assert resp.status_code == 200
        data = resp.json()["data"]
        account_ids = [a["id"] for a in data]

        assert str(account_in_a.id) in account_ids
        assert str(account_in_b.id) not in account_ids

        _clear_overrides()

    def test_get_account_from_other_workspace_returns_404(
        self, client, db_session, workspace_a, workspace_b, account_in_b
    ):
        """Requesting an account from workspace B while in workspace A must 404."""
        _setup_overrides(db_session, workspace_a)

        resp = client.get(f"/accounts/{account_in_b.id}")
        assert resp.status_code == 404

        _clear_overrides()

    def test_dashboard_only_returns_own_workspace(
        self, client, db_session, workspace_a, workspace_b, account_in_a, account_in_b
    ):
        """Dashboard must only show accounts from the active workspace."""
        _setup_overrides(db_session, workspace_a)

        resp = client.get("/accounts/dashboard")
        assert resp.status_code == 200
        data = resp.json()["data"]
        names = [a["name"] for a in data]

        assert "Acme Corp (A)" in names
        assert "Beta Inc (B)" not in names

        _clear_overrides()


# ── Signals isolation ────────────────────────────────────────────────────

class TestSignalIsolation:
    def test_list_signals_only_returns_own_workspace(
        self, client, db_session, workspace_a, workspace_b,
        account_in_a, account_in_b, signal_in_a, signal_in_b
    ):
        """Listing signals in workspace A must not include workspace B signals."""
        _setup_overrides(db_session, workspace_a)

        resp = client.get("/signals")
        assert resp.status_code == 200
        data = resp.json()["data"]
        signal_ids = [s["id"] for s in data]

        assert str(signal_in_a.id) in signal_ids
        assert str(signal_in_b.id) not in signal_ids

        _clear_overrides()

    def test_get_signal_from_other_workspace_returns_404(
        self, client, db_session, workspace_a, workspace_b,
        account_in_b, signal_in_b
    ):
        """Requesting a signal from workspace B while in workspace A must 404."""
        _setup_overrides(db_session, workspace_a)

        resp = client.get(f"/signals/{signal_in_b.id}")
        assert resp.status_code == 404

        _clear_overrides()


# ── Evidence isolation ───────────────────────────────────────────────────

class TestEvidenceIsolation:
    def test_evidence_from_other_workspace_returns_404(
        self, client, db_session, workspace_a, workspace_b,
        account_in_b, signal_in_b
    ):
        """Evidence endpoint for a signal in workspace B must 404 in workspace A."""
        _setup_overrides(db_session, workspace_a)

        resp = client.get(f"/signals/{signal_in_b.id}/evidence")
        assert resp.status_code == 404

        _clear_overrides()

    def test_evidence_for_own_signal_returns_200(
        self, client, db_session, workspace_a, account_in_a, signal_in_a
    ):
        """Evidence endpoint for a signal in own workspace must return 200."""
        _setup_overrides(db_session, workspace_a)

        resp = client.get(f"/signals/{signal_in_a.id}/evidence")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["signalId"] == str(signal_in_a.id)
        assert data["signalType"] == "funding"

        _clear_overrides()
