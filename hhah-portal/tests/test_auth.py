"""Auth flow tests — login, MFA challenge, logout, invite consume."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pyotp
from sqlalchemy import select

from app.models.user import Invite, User
from app.services import auth_service as auth


def test_login_page_accessible_without_auth(client):
    r = client.get("/login", follow_redirects=False)
    assert r.status_code == 200
    assert "Welcome back" in r.text


def test_login_redirects_to_dashboard_when_authed(authed_client):
    r = authed_client.get("/login", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/"


def test_login_with_wrong_password_returns_400(client, admin_user):
    r = client.post("/login", data={"email": admin_user.email, "password": "wrong"},
                    follow_redirects=False)
    assert r.status_code == 400
    assert "Invalid" in r.text


def test_login_success_routes_to_mfa_challenge(client, admin_user):
    r = client.post("/login",
                    data={"email": admin_user.email, "password": "test-password-12345"},
                    follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/auth/mfa/challenge"


def test_mfa_challenge_with_valid_totp_logs_in(client, admin_user):
    # First login (no mfa) sets cookie
    r = client.post("/login",
                    data={"email": admin_user.email, "password": "test-password-12345"},
                    follow_redirects=False)
    assert r.status_code == 303
    code = pyotp.TOTP(admin_user.mfa_totp_secret).now()
    r = client.post("/auth/mfa/challenge", data={"code": code}, follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/"


def test_logout_clears_cookies(authed_client):
    r = authed_client.post("/logout", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/login"


def test_invite_consume_creates_user_and_logs_in(db, org, admin_user):
    inv, raw = auth.issue_invite(
        db, org_id=org.id, email="invitee@test.local",
        role="hhah_user", issued_by=admin_user.id,
    )
    db.commit()

    user = auth.consume_invite(
        db, raw_token=raw, password="strong-test-pw-12345",
        display_name="New Joiner",
    )
    db.commit()
    assert user.email == "invitee@test.local"
    assert user.role == "hhah_user"
    refreshed = db.scalar(select(Invite).where(Invite.id == inv.id))
    assert refreshed.consumed_at is not None


def test_invite_cannot_be_reused(db, org, admin_user):
    _, raw = auth.issue_invite(db, org_id=org.id, email="x@test.local",
                                role="hhah_user", issued_by=admin_user.id)
    db.commit()
    auth.consume_invite(db, raw_token=raw, password="strong-test-pw-12345",
                        display_name="X")
    db.commit()
    try:
        auth.consume_invite(db, raw_token=raw, password="another-pw-12345",
                            display_name="Imposter")
    except auth.AuthError as e:
        assert "already_used" in str(e)
        return
    raise AssertionError("expected AuthError")


def test_expired_invite_rejected(db, org, admin_user):
    inv, raw = auth.issue_invite(db, org_id=org.id, email="late@test.local",
                                  role="hhah_user", issued_by=admin_user.id)
    inv.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()
    try:
        auth.consume_invite(db, raw_token=raw, password="pw-12345-strong",
                            display_name="Late")
    except auth.AuthError as e:
        assert "expired" in str(e)
        return
    raise AssertionError("expected AuthError")
