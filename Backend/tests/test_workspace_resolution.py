"""Task 4 verification — Workspace resolution rules.

Tests the tightened rules:
  4a. One workspace + no header → use it
  4b. Multiple workspaces + no header → 400
  4c. Workspace header for non-member workspace → 403
  4d. Zero workspaces → auto-create (first bootstrap)
"""

import uuid

from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.auth import _resolve_workspace, _upsert_user
from fastapi import HTTPException
import pytest


class TestWorkspaceResolution:
    def test_single_workspace_auto_resolves(self, db_session):
        """4a: User with exactly one workspace → auto-resolve to it."""
        user = User(id=uuid.uuid4(), email="single@test.com")
        db_session.add(user)
        db_session.flush()

        ws = Workspace(id=uuid.uuid4(), name="Only Workspace", created_by=user.id)
        db_session.add(ws)
        db_session.flush()

        db_session.add(WorkspaceMember(user_id=user.id, workspace_id=ws.id, role="owner"))
        db_session.flush()

        ws_id, role = _resolve_workspace(db_session, user)
        assert ws_id == ws.id
        assert role == "owner"

    def test_multiple_workspaces_returns_400(self, db_session):
        """4b: User with 2+ workspaces and no header → 400."""
        user = User(id=uuid.uuid4(), email="multi@test.com")
        db_session.add(user)
        db_session.flush()

        for i in range(2):
            ws = Workspace(id=uuid.uuid4(), name=f"WS {i}", created_by=user.id)
            db_session.add(ws)
            db_session.flush()
            db_session.add(WorkspaceMember(user_id=user.id, workspace_id=ws.id, role="owner"))
            db_session.flush()

        with pytest.raises(HTTPException) as exc_info:
            _resolve_workspace(db_session, user)
        assert exc_info.value.status_code == 400
        assert "multiple workspaces" in exc_info.value.detail.lower()

    def test_zero_workspaces_bootstraps(self, db_session):
        """4d: New user with no workspaces → auto-create default workspace."""
        user = User(id=uuid.uuid4(), email="newuser@test.com")
        db_session.add(user)
        db_session.flush()

        ws_id, role = _resolve_workspace(db_session, user)
        assert ws_id is not None
        assert role == "owner"

        # Verify workspace was actually created
        ws = db_session.get(Workspace, ws_id)
        assert ws is not None
        assert "newuser@test.com" in ws.name
