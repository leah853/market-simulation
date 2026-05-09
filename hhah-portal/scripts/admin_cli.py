"""Eonexea ops CLI — provision a new HHAH org, invite users.

Examples:
  python -m scripts.admin_cli new-org --name "Sunrise Home Health" --slug sunrise
  python -m scripts.admin_cli invite  --org-slug sunrise --email lisa@sun.com --role hhah_admin
  python -m scripts.admin_cli list-orgs
  python -m scripts.admin_cli list-users --org-slug sunrise
"""
from __future__ import annotations

import argparse
import sys
from uuid import UUID

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.organization import Organization
from app.models.user import User
from app.services import auth_service as auth


def _org_by_slug(db, slug: str) -> Organization:
    org = db.scalar(select(Organization).where(Organization.slug == slug))
    if not org:
        sys.stderr.write(f"❌ org slug '{slug}' not found\n")
        sys.exit(2)
    return org


def cmd_new_org(args: argparse.Namespace) -> int:
    with SessionLocal() as db:
        if db.scalar(select(Organization).where(Organization.slug == args.slug)):
            print(f"⚠ org slug '{args.slug}' already exists")
            return 1
        org = Organization(
            name=args.name,
            slug=args.slug,
            tenancy_mode="single_tenant_multi_hhah",
        )
        db.add(org); db.commit()
        print(f"✓ Org created")
        print(f"  id:   {org.id}")
        print(f"  name: {org.name}")
        print(f"  slug: {org.slug}")
    return 0


def cmd_invite(args: argparse.Namespace) -> int:
    if args.role not in {"hhah_admin", "hhah_user"}:
        sys.stderr.write("role must be hhah_admin or hhah_user\n")
        return 2
    with SessionLocal() as db:
        org = _org_by_slug(db, args.org_slug)
        inv, raw = auth.issue_invite(
            db, org_id=org.id, email=args.email, role=args.role,
        )
        db.commit()
        s = get_settings()
        link = f"{s.app_base_url}/invite/accept?token={raw}"
        print(f"✓ Invite issued")
        print(f"  org:   {org.name}")
        print(f"  email: {args.email}")
        print(f"  role:  {args.role}")
        print(f"  expires: {inv.expires_at.isoformat()} (24h)")
        print(f"\n  Share this link (single-use):")
        print(f"  {link}")
    return 0


def cmd_list_orgs(_: argparse.Namespace) -> int:
    with SessionLocal() as db:
        rows = list(db.scalars(select(Organization).order_by(Organization.created_at.desc())))
        if not rows:
            print("(no orgs)")
            return 0
        print(f"{'SLUG':<24} {'NAME':<40} ID")
        for o in rows:
            print(f"{o.slug:<24} {o.name:<40} {o.id}")
    return 0


def cmd_list_users(args: argparse.Namespace) -> int:
    with SessionLocal() as db:
        org = _org_by_slug(db, args.org_slug)
        rows = list(db.scalars(
            select(User).where(User.org_id == org.id, User.deleted_at.is_(None))
        ))
        print(f"Org: {org.name} ({org.slug})  —  {len(rows)} users")
        for u in rows:
            mfa = "✓" if u.mfa_totp_enrolled else "·"
            print(f"  [{u.role:<10}] {mfa} {u.email:<40} {u.display_name}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(prog="admin_cli", description="Eonexea ops CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_new = sub.add_parser("new-org", help="Provision a new HHAH org")
    p_new.add_argument("--name", required=True)
    p_new.add_argument("--slug", required=True)
    p_new.set_defaults(func=cmd_new_org)

    p_inv = sub.add_parser("invite", help="Issue a 24h invite link")
    p_inv.add_argument("--org-slug", required=True)
    p_inv.add_argument("--email", required=True)
    p_inv.add_argument("--role", default="hhah_user")
    p_inv.set_defaults(func=cmd_invite)

    p_lo = sub.add_parser("list-orgs", help="List all organizations")
    p_lo.set_defaults(func=cmd_list_orgs)

    p_lu = sub.add_parser("list-users", help="List users for an org")
    p_lu.add_argument("--org-slug", required=True)
    p_lu.set_defaults(func=cmd_list_users)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
