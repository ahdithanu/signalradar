"""Authentication and workspace context for multi-tenant routes.

Two modes:
  1. auth_enabled=True  → validates Supabase JWT, upserts User, resolves workspace
  2. auth_enabled=False → returns a default dev user + workspace (local dev only)

Usage in routes:
    @router.get("/stuff")
    def get_stuff(ctx: WorkspaceContext = Depends(get_workspace_context)):
        db = ctx.db
        workspace_id = ctx.workspace_id
        ...
"""

from __future__ import annotations

import json
import logging
import time
import urllib.request
import uuid
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember

logger = logging.getLogger(__name__)

# Deterministic IDs for local dev mode (auth_enabled=False)
DEFAULT_USER_ID = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001")
DEFAULT_WORKSPACE_ID = uuid.UUID("bbbbbbbb-0000-0000-0000-000000000001")


@dataclass
class WorkspaceContext:
    """Injected into every authenticated route."""
    user: User
    workspace_id: uuid.UUID
    role: str
    db: Session


# JWKS cache for asymmetric Supabase JWT verification.
# Supabase projects created after their 2025 asymmetric-key rollout sign JWTs
# with an ES256 key; the shared HS256 `SUPABASE_JWT_SECRET` no longer applies.
# We fetch the public keys once per hour and match tokens by `kid`.
_JWKS_TTL_SEC = 3600
_ASYMMETRIC_ALGS = {"ES256", "RS256", "EdDSA"}
_jwks_cache: dict | None = None
_jwks_fetched_at: float = 0.0


def _fetch_jwks(force: bool = False) -> dict:
    global _jwks_cache, _jwks_fetched_at
    now = time.time()
    if _jwks_cache is not None and not force and (now - _jwks_fetched_at) < _JWKS_TTL_SEC:
        return _jwks_cache
    if not settings.supabase_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SUPABASE_URL is not configured",
        )
    url = f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
    with urllib.request.urlopen(url, timeout=5) as resp:
        _jwks_cache = json.loads(resp.read())
    _jwks_fetched_at = now
    return _jwks_cache


def _find_jwk_for_kid(kid: str) -> dict | None:
    jwks = _fetch_jwks()
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key
    # kid not found — key may have rotated; force one refresh and retry
    jwks = _fetch_jwks(force=True)
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key
    return None


def _decode_supabase_jwt(token: str) -> dict:
    """Decode and validate a Supabase JWT. Returns claims dict.

    Supports both signing modes:
      - Asymmetric (ES256/RS256/EdDSA): verify via JWKS public key
      - Legacy HS256: verify via SUPABASE_JWT_SECRET
    """
    try:
        header = jwt.get_unverified_header(token)
    except JWTError as e:
        logger.warning("JWT header parse failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    alg = (header.get("alg") or "").upper()
    kid = header.get("kid")

    if alg in _ASYMMETRIC_ALGS:
        if not kid:
            logger.warning("Asymmetric token missing 'kid' header")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )
        key = _find_jwk_for_kid(kid)
        if key is None:
            logger.warning("JWT kid %s not found in JWKS", kid)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unknown token signing key",
            )
        try:
            return jwt.decode(
                token,
                key,
                algorithms=[alg],
                audience="authenticated",
            )
        except JWTError as e:
            logger.warning("JWT decode failed (%s): %s", alg, e)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )

    if alg == "HS256":
        if not settings.supabase_jwt_secret:
            logger.warning("HS256 token but SUPABASE_JWT_SECRET is not set")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Server not configured for HS256 tokens",
            )
        try:
            return jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                audience="authenticated",
            )
        except JWTError as e:
            logger.warning("JWT decode failed (HS256): %s", e)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )

    logger.warning("Unsupported JWT alg: %s", alg)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=f"Unsupported token algorithm: {alg}",
    )


def _upsert_user(db: Session, user_id: uuid.UUID, email: str) -> User:
    """Get existing user or create one from JWT claims."""
    user = db.get(User, user_id)
    if user is None:
        user = User(id=user_id, email=email)
        db.add(user)
        db.flush()
        logger.info("Created new user: %s (%s)", user_id, email)
    elif user.email != email:
        user.email = email
        db.flush()
    return user


def _resolve_workspace(db: Session, user: User) -> tuple[uuid.UUID, str]:
    """Resolve workspace for an authenticated user with no X-Workspace-Id header.

    Rules:
      - 0 workspaces → auto-create a default (first bootstrap only)
      - 1 workspace  → use it
      - 2+ workspaces → return 400 (must specify X-Workspace-Id)
    """
    memberships = db.scalars(
        select(WorkspaceMember).where(WorkspaceMember.user_id == user.id)
    ).all()

    if len(memberships) == 1:
        return memberships[0].workspace_id, memberships[0].role

    if len(memberships) > 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "You belong to multiple workspaces. "
                "Provide X-Workspace-Id header to specify which one."
            ),
        )

    # No memberships — first-time bootstrap: create default workspace
    workspace = Workspace(
        name=f"{user.email}'s workspace",
        created_by=user.id,
    )
    db.add(workspace)
    db.flush()

    member = WorkspaceMember(
        user_id=user.id,
        workspace_id=workspace.id,
        role="owner",
    )
    db.add(member)
    db.flush()
    logger.info("Bootstrap: created default workspace %s for user %s", workspace.id, user.id)
    return workspace.id, "owner"


def _ensure_dev_context(db: Session) -> WorkspaceContext:
    """Create or retrieve default dev user + workspace (auth_enabled=False)."""
    user = db.get(User, DEFAULT_USER_ID)
    if user is None:
        user = User(id=DEFAULT_USER_ID, email="dev@signalradar.local", display_name="Dev User")
        db.add(user)
        db.flush()

    workspace = db.get(Workspace, DEFAULT_WORKSPACE_ID)
    if workspace is None:
        workspace = Workspace(id=DEFAULT_WORKSPACE_ID, name="Dev Workspace", created_by=user.id)
        db.add(workspace)
        db.flush()

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
        db.flush()

    db.commit()
    return WorkspaceContext(
        user=user,
        workspace_id=DEFAULT_WORKSPACE_ID,
        role="owner",
        db=db,
    )


@dataclass
class AuthenticatedUser:
    """Lightweight auth result — user only, no workspace resolution.
    Used for endpoints that don't need workspace scoping (e.g., list workspaces).
    """
    user: User
    db: Session


def get_authenticated_user(
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
) -> AuthenticatedUser:
    """FastAPI dependency — validates JWT and returns user, without workspace resolution.

    Used for endpoints like GET /workspaces where the user needs to list
    their workspaces before selecting one.
    """
    if not settings.auth_enabled:
        ctx = _ensure_dev_context(db)
        return AuthenticatedUser(user=ctx.user, db=db)

    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format (expected 'Bearer <token>')",
        )
    token = parts[1]

    claims = _decode_supabase_jwt(token)
    user_id_str = claims.get("sub")
    email = claims.get("email", "")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing 'sub' claim",
        )

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token",
        )

    user = _upsert_user(db, user_id, email)
    db.commit()
    return AuthenticatedUser(user=user, db=db)


def get_workspace_context(
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
) -> WorkspaceContext:
    """FastAPI dependency — resolves authenticated user + workspace.

    When auth_enabled=False, returns a dev context without JWT validation.
    """
    if not settings.auth_enabled:
        ctx = _ensure_dev_context(db)
        # In dev mode, honor X-Workspace-Id if provided and dev user is a member
        if x_workspace_id:
            try:
                ws_id = uuid.UUID(x_workspace_id)
            except ValueError:
                return ctx
            membership = db.scalar(
                select(WorkspaceMember).where(
                    WorkspaceMember.user_id == ctx.user.id,
                    WorkspaceMember.workspace_id == ws_id,
                )
            )
            if membership:
                return WorkspaceContext(
                    user=ctx.user,
                    workspace_id=ws_id,
                    role=membership.role,
                    db=db,
                )
        return ctx

    # --- Auth enabled: validate JWT ---
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )

    # Extract Bearer token
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format (expected 'Bearer <token>')",
        )
    token = parts[1]

    claims = _decode_supabase_jwt(token)
    user_id_str = claims.get("sub")
    email = claims.get("email", "")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing 'sub' claim",
        )

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token",
        )

    user = _upsert_user(db, user_id, email)

    # --- Resolve workspace ---
    if x_workspace_id:
        try:
            workspace_id = uuid.UUID(x_workspace_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid X-Workspace-Id header",
            )

        membership = db.scalar(
            select(WorkspaceMember).where(
                WorkspaceMember.user_id == user.id,
                WorkspaceMember.workspace_id == workspace_id,
            )
        )
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this workspace",
            )
        db.commit()
        return WorkspaceContext(
            user=user,
            workspace_id=workspace_id,
            role=membership.role,
            db=db,
        )

    # No workspace header — resolve by membership count
    ws_id, role = _resolve_workspace(db, user)
    db.commit()
    return WorkspaceContext(user=user, workspace_id=ws_id, role=role, db=db)
