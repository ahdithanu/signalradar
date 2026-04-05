"""Workspace management endpoints.

GET /workspaces uses AuthenticatedUser (no workspace required).
POST /workspaces uses AuthenticatedUser (creates a new workspace).
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from app.auth import AuthenticatedUser, get_authenticated_user, WorkspaceContext, get_workspace_context
from app.models.workspace import Workspace, WorkspaceMember

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


class WorkspaceOut(BaseModel):
    id: uuid.UUID
    name: str
    role: str
    createdAt: str


class WorkspaceCreate(BaseModel):
    name: str


@router.get("")
def list_workspaces(auth: AuthenticatedUser = Depends(get_authenticated_user)):
    """List all workspaces the current user belongs to.

    Uses lightweight auth — no workspace resolution required.
    This allows multi-workspace users to list their workspaces
    before selecting one.
    """
    db = auth.db
    memberships = db.scalars(
        select(WorkspaceMember).where(WorkspaceMember.user_id == auth.user.id)
    ).all()

    result = []
    for m in memberships:
        ws = db.get(Workspace, m.workspace_id)
        if ws:
            result.append(WorkspaceOut(
                id=ws.id,
                name=ws.name,
                role=m.role,
                createdAt=ws.created_at.isoformat(),
            ))
    return {"data": result}


@router.post("", status_code=201)
def create_workspace(
    body: WorkspaceCreate,
    auth: AuthenticatedUser = Depends(get_authenticated_user),
):
    """Create a new workspace and make the current user the owner."""
    db = auth.db
    workspace = Workspace(name=body.name, created_by=auth.user.id)
    db.add(workspace)
    db.flush()

    member = WorkspaceMember(
        user_id=auth.user.id,
        workspace_id=workspace.id,
        role="owner",
    )
    db.add(member)
    db.commit()

    return {
        "data": WorkspaceOut(
            id=workspace.id,
            name=workspace.name,
            role="owner",
            createdAt=workspace.created_at.isoformat(),
        )
    }
