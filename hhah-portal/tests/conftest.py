"""Shared pytest fixtures.

Tests run against a real Postgres test database. Set TEST_DATABASE_URL or
fall back to:  postgresql+psycopg://hhah:hhah@localhost:5432/hhah_portal_test

Run from repo root:
  createdb hhah_portal_test
  pytest
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Force test DB URL before app/config import
TEST_DB = os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://hhah:hhah@localhost:5432/hhah_portal_test",
)
os.environ.setdefault("APP_ENV", "local")
os.environ.setdefault("JWT_SECRET", "test-secret-not-for-prod")

from app.core.security import hash_password
from app.db.base import Base
from app.db import session as db_session
from app.main import app
from app.models.organization import Organization
from app.models.user import User


@pytest.fixture(scope="session")
def engine():
    eng = create_engine(TEST_DB)
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)


@pytest.fixture
def db(engine, monkeypatch) -> Session:
    """Per-test session, rolled back at the end."""
    SessionMaker = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    db = SessionMaker()

    # Patch get_db to yield this session
    def _override():
        try:
            yield db
        finally:
            pass
    app.dependency_overrides[db_session.get_db] = _override

    yield db

    db.rollback()
    # Cleanup all data
    for tbl in reversed(Base.metadata.sorted_tables):
        db.execute(tbl.delete())
    db.commit()
    db.close()
    app.dependency_overrides.pop(db_session.get_db, None)


@pytest.fixture
def org(db) -> Organization:
    o = Organization(name="Test HHAH", slug=f"test-{uuid4().hex[:6]}")
    db.add(o)
    db.commit()
    return o


@pytest.fixture
def admin_user(db, org) -> User:
    u = User(
        org_id=org.id,
        email=f"admin-{uuid4().hex[:6]}@test.local",
        display_name="Admin Test",
        password_hash=hash_password("test-password-12345"),
        role="hhah_admin",
        is_active=True,
        mfa_totp_enrolled=True,
        mfa_totp_secret="JBSWY3DPEHPK3PXP",  # known test secret
        accepted_terms_at=datetime.now(timezone.utc),
    )
    db.add(u)
    db.commit()
    return u


@pytest.fixture
def hhah_user(db, org) -> User:
    u = User(
        org_id=org.id,
        email=f"user-{uuid4().hex[:6]}@test.local",
        display_name="Regular User",
        password_hash=hash_password("test-password-12345"),
        role="hhah_user",
        is_active=True,
        mfa_totp_enrolled=True,
        mfa_totp_secret="JBSWY3DPEHPK3PXP",
        accepted_terms_at=datetime.now(timezone.utc),
    )
    db.add(u)
    db.commit()
    return u


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def authed_client(client, admin_user) -> TestClient:
    """Test client with an authenticated mfa-verified session for admin_user."""
    from app.core.permissions import permissions_for
    from app.core.security import issue_access_token, issue_refresh_token

    access, _ = issue_access_token(
        user_id=admin_user.id,
        org_id=admin_user.org_id,
        role=admin_user.role,
        permissions=permissions_for(admin_user.role),
        mfa_verified=True,
    )
    refresh, _ = issue_refresh_token(user_id=admin_user.id, session_id=uuid4())
    client.cookies.set("access_token", access)
    client.cookies.set("refresh_token", refresh)
    return client


@pytest.fixture
def authed_user_client(client, hhah_user) -> TestClient:
    """Authenticated client for hhah_user (no admin perms)."""
    from app.core.permissions import permissions_for
    from app.core.security import issue_access_token, issue_refresh_token

    access, _ = issue_access_token(
        user_id=hhah_user.id,
        org_id=hhah_user.org_id,
        role=hhah_user.role,
        permissions=permissions_for(hhah_user.role),
        mfa_verified=True,
    )
    refresh, _ = issue_refresh_token(user_id=hhah_user.id, session_id=uuid4())
    client.cookies.set("access_token", access)
    client.cookies.set("refresh_token", refresh)
    return client
