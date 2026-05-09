"""Dev seed — creates an Org, an Admin user, and prints an invite link.

Run with:  python -m scripts.seed
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.organization import Organization
from app.models.user import User
from app.services import auth_service as auth


def main() -> int:
    settings = get_settings()
    print(f"Seeding {settings.app_env} db: {settings.database_url}")

    with SessionLocal() as db:
        # Org
        org = db.scalar(select(Organization).where(Organization.slug == "sunrise-hh"))
        if not org:
            org = Organization(
                name="Sunrise Home Health",
                slug="sunrise-hh",
                tenancy_mode="single_tenant_multi_hhah",
            )
            db.add(org)
            db.flush()
            print(f"  ✓ Org created: {org.name}  (id={org.id})")
        else:
            print(f"  · Org exists: {org.name}")

        # Admin user (password: admin123!)
        admin = db.scalar(select(User).where(User.email == "admin@sunrise-hh.com"))
        if not admin:
            admin = User(
                org_id=org.id,
                email="admin@sunrise-hh.com",
                display_name="Lisa Chen",
                password_hash=hash_password("admin123!"),
                role="hhah_admin",
                is_active=True,
                accepted_terms_at=datetime.now(timezone.utc),
            )
            db.add(admin)
            db.flush()
            print(f"  ✓ Admin user created: {admin.email}  password=admin123!")
        else:
            print(f"  · Admin exists: {admin.email}")

        # Regular user
        regular = db.scalar(select(User).where(User.email == "user@sunrise-hh.com"))
        if not regular:
            regular = User(
                org_id=org.id,
                email="user@sunrise-hh.com",
                display_name="Maria Rodriguez",
                password_hash=hash_password("user123!"),
                role="hhah_user",
                is_active=True,
                accepted_terms_at=datetime.now(timezone.utc),
            )
            db.add(regular)
            db.flush()
            print(f"  ✓ Regular user created: {regular.email}  password=user123!")
        else:
            print(f"  · Regular user exists: {regular.email}")

        # Issue an invite for testing the invite-accept flow
        inv, raw = auth.issue_invite(
            db, org_id=org.id,
            email=f"newuser-{uuid4().hex[:6]}@sunrise-hh.com",
            role="hhah_user",
            issued_by=admin.id,
        )
        print(f"  ✓ Invite issued for: {inv.email}")
        print(f"      raw token (24h, single-use): {raw}")

        db.commit()

    print("\n✅ Seed complete. Sign in:")
    print("   Admin: admin@sunrise-hh.com / admin123!")
    print("   User : user@sunrise-hh.com / user123!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
