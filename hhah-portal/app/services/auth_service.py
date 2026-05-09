"""Authentication service — login, MFA, sessions, invites."""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

import pyotp
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import write_audit
from app.core.config import get_settings
from app.core.permissions import permissions_for
from app.core.security import (
    hash_password, issue_access_token, issue_refresh_token,
    verify_password,
)
from app.models.user import Invite, Session as UserSession, User


# ─── Login ──────────────────────────────────────────────────────────

class AuthError(Exception):
    pass


def authenticate(db: Session, *, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == email.lower(), User.deleted_at.is_(None)))
    if not user or not user.password_hash:
        raise AuthError("invalid_credentials")
    if not user.is_active:
        raise AuthError("account_disabled")
    if not verify_password(password, user.password_hash):
        raise AuthError("invalid_credentials")
    user.last_login_at = datetime.now(timezone.utc)
    return user


def issue_session(
    db: Session,
    *,
    user: User,
    mfa_verified: bool,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> tuple[str, str, UserSession]:
    """Returns (access_token, refresh_token, session)."""
    s = get_settings()
    now = datetime.now(timezone.utc)

    sess = UserSession(
        user_id=user.id,
        ip_address=ip_address,
        user_agent=user_agent,
        last_seen_at=now,
        expires_at=now + timedelta(hours=s.session_absolute_hours),
        mfa_verified=mfa_verified,
    )
    db.add(sess)
    db.flush()

    access, _ = issue_access_token(
        user_id=user.id,
        org_id=user.org_id,
        role=user.role,
        permissions=permissions_for(user.role),
        mfa_verified=mfa_verified,
    )
    refresh, _ = issue_refresh_token(user_id=user.id, session_id=sess.id)

    write_audit(
        db,
        org_id=user.org_id,
        actor_user_id=user.id,
        action_type="session.created",
        subject_type="user",
        subject_id=user.id,
        subject_label=user.email,
        ip_address=ip_address,
        user_agent=user_agent,
        details={"mfa_verified": mfa_verified},
    )
    return access, refresh, sess


# ─── MFA (TOTP) ─────────────────────────────────────────────────────

def begin_totp_enrollment(db: Session, user: User) -> tuple[str, str]:
    """Returns (secret, otpauth_uri). Caller renders QR + verify form."""
    secret = pyotp.random_base32()
    user.mfa_totp_secret = secret  # not yet committed as enrolled
    issuer = get_settings().app_brand
    uri = pyotp.totp.TOTP(secret).provisioning_uri(name=user.email, issuer_name=issuer)
    return secret, uri


def verify_totp(user: User, code: str) -> bool:
    if not user.mfa_totp_secret:
        return False
    totp = pyotp.TOTP(user.mfa_totp_secret)
    return totp.verify(code, valid_window=1)


def confirm_totp_enrollment(db: Session, user: User, code: str) -> list[str]:
    """Verifies the first code and finalizes enrollment. Returns recovery codes."""
    if not verify_totp(user, code):
        raise AuthError("invalid_totp")
    user.mfa_totp_enrolled = True
    codes = [secrets.token_urlsafe(6) for _ in range(8)]
    user.mfa_recovery_codes_hashed = ",".join(
        hashlib.sha256(c.encode()).hexdigest() for c in codes
    )
    write_audit(
        db, org_id=user.org_id, actor_user_id=user.id,
        action_type="mfa.enrolled", subject_type="user", subject_id=user.id,
        subject_label=user.email, details={"method": "totp"},
    )
    return codes


# ─── Invites ────────────────────────────────────────────────────────

def issue_invite(
    db: Session,
    *,
    org_id: UUID,
    email: str,
    role: str,
    issued_by: Optional[UUID] = None,
) -> tuple[Invite, str]:
    """Returns (invite, raw_token). Token is what goes in the email link;
    hash is stored. 24-hour single-use."""
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    inv = Invite(
        org_id=org_id,
        email=email.lower(),
        role=role,
        token_hash=token_hash,
        expires_at=Invite.default_expiry(),
        created_by_user_id=issued_by,
    )
    db.add(inv)
    db.flush()
    write_audit(
        db, org_id=org_id, actor_user_id=issued_by,
        action_type="invite.issued", subject_type="invite", subject_id=inv.id,
        subject_label=email, details={"role": role, "expires_at": inv.expires_at.isoformat()},
    )
    return inv, raw_token


def consume_invite(
    db: Session,
    *,
    raw_token: str,
    password: str,
    display_name: str,
) -> User:
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    inv = db.scalar(select(Invite).where(Invite.token_hash == token_hash))
    if not inv:
        raise AuthError("invite_invalid")
    if inv.consumed_at is not None:
        raise AuthError("invite_already_used")
    if inv.expires_at < datetime.now(timezone.utc):
        raise AuthError("invite_expired")

    # Create user
    user = User(
        org_id=inv.org_id,
        email=inv.email,
        display_name=display_name,
        password_hash=hash_password(password),
        role=inv.role,
        is_active=True,
        accepted_terms_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.flush()

    inv.consumed_at = datetime.now(timezone.utc)

    write_audit(
        db, org_id=inv.org_id, actor_user_id=user.id,
        action_type="invite.consumed", subject_type="user", subject_id=user.id,
        subject_label=user.email,
    )
    return user
