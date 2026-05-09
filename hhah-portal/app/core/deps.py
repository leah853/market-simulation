"""FastAPI dependencies — current user, permission gates, audit context."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from fastapi import Cookie, Depends, HTTPException, Request, status

from app.core.security import decode_token


@dataclass(frozen=True, slots=True)
class CurrentUser:
    user_id: UUID
    org_id: UUID
    role: str
    permissions: frozenset[str]
    mfa_verified: bool

    def has(self, permission: str) -> bool:
        return permission in self.permissions


def _decode_or_none(token: Optional[str]) -> Optional[dict]:
    if not token:
        return None
    try:
        return decode_token(token)
    except Exception:
        return None


def get_current_user_optional(
    request: Request,
    access_token: Optional[str] = Cookie(default=None),
) -> Optional[CurrentUser]:
    """Returns CurrentUser or None — used on public routes that personalize."""
    # Prefer Authorization header, fall back to cookie (for HTMX page navigation)
    bearer = request.headers.get("authorization", "")
    token = bearer.removeprefix("Bearer ").strip() if bearer.startswith("Bearer ") else access_token
    payload = _decode_or_none(token)
    if not payload or payload.get("type") != "access":
        return None
    return CurrentUser(
        user_id=UUID(payload["sub"]),
        org_id=UUID(payload["org_id"]),
        role=payload["role"],
        permissions=frozenset(payload.get("perms", [])),
        mfa_verified=bool(payload.get("mfa", False)),
    )


def get_current_user(
    user: Optional[CurrentUser] = Depends(get_current_user_optional),
) -> CurrentUser:
    """Required — 401 if missing."""
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not authenticated")
    if not user.mfa_verified:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="mfa required")
    return user


def require_permissions(*perms: str):
    """Dependency factory: require_permissions('flag.create', ...)."""
    def _check(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        for p in perms:
            if not user.has(p):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"missing permission: {p}",
                )
        return user
    return _check
