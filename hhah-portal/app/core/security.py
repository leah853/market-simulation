"""Password hashing, JWT issuance, and verification."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import jwt
from passlib.context import CryptContext

from app.core.config import get_settings

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return _pwd.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd.verify(plain, hashed)


def issue_access_token(
    *,
    user_id: UUID,
    org_id: UUID,
    role: str,
    permissions: list[str],
    mfa_verified: bool,
) -> tuple[str, datetime]:
    """Returns (token, expires_at)."""
    s = get_settings()
    now = datetime.now(timezone.utc)
    exp = now + timedelta(seconds=s.jwt_access_ttl_seconds)
    payload = {
        "sub": str(user_id),
        "org_id": str(org_id),
        "role": role,
        "perms": permissions,
        "mfa": mfa_verified,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "type": "access",
    }
    token = jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_algorithm)
    return token, exp


def issue_refresh_token(*, user_id: UUID, session_id: UUID) -> tuple[str, datetime]:
    s = get_settings()
    now = datetime.now(timezone.utc)
    exp = now + timedelta(seconds=s.jwt_refresh_ttl_seconds)
    payload = {
        "sub": str(user_id),
        "sid": str(session_id),
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "type": "refresh",
    }
    return jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_algorithm), exp


def decode_token(token: str) -> dict[str, Any]:
    s = get_settings()
    return jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_algorithm])
