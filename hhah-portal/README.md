# Eonexea HHAH Portal — V1

Python-friendly thin client for HHAH staff. **FastAPI · HTMX · Jinja · Tailwind · SQLAlchemy 2 · Alembic · Postgres.**

This portal does **not** run the Eonexea workflow orchestrator — it's a thin authenticated UI layer that reads from and dispatches to the orchestrator. All writes flow through workflows on the orchestrator side.

---

## Quick start

```bash
# 1. Python env
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# 2. Postgres (local)
createdb hhah_portal
createuser hhah --pwprompt    # set password to 'hhah' to match .env.example

# 3. Configure
cp .env.example .env
# edit .env if your Postgres URL differs

# 4. Migrations
alembic revision --autogenerate -m "init schema"
alembic upgrade head

# 5. Seed (creates an Org + admin + user + invite)
python -m scripts.seed

# 6. Run
uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000 — you'll be redirected to `/login`.

**Test credentials** (from seed):
```
admin@sunrise-hh.com / admin123!
user@sunrise-hh.com  / user123!
```

The first sign-in flows through MFA enrollment (TOTP via any authenticator app).

---

## Project layout

```
app/
├── main.py                      FastAPI entrypoint
├── api/
│   ├── routes/
│   │   ├── auth.py              login / mfa / invite-accept / logout
│   │   └── dashboard.py         empty + active dashboard
│   └── templating.py            Jinja helpers + HTMX detection
├── core/
│   ├── config.py                Settings (env-driven)
│   ├── security.py              hashing + JWT
│   ├── permissions.py           Permission strings + role bundles
│   ├── deps.py                  FastAPI deps (current user, perm gates)
│   └── audit.py                 Audit + PHI access logging
├── db/
│   ├── base.py                  declarative base + mixins
│   ├── session.py               session factory
│   └── migrations/              Alembic
├── models/                      Domain entities
│   ├── organization.py          Organization + BAARecord
│   ├── user.py                  User + Session + Invite
│   ├── practitioner.py          Practitioner + PracticeOrg + PG-membership
│   ├── patient.py               Patient (with PG↔Practitioner attribution)
│   ├── admission.py             Admission + Episode (single-table-with-status)
│   ├── document.py              Document + Comment
│   ├── signature.py             SignatureRequest
│   ├── flag.py                  Flag (polymorphic, multi-source resolution)
│   ├── communication.py         Thread + Message
│   ├── notification.py          Notification
│   ├── audit.py                 AuditLog + PHIAccessLog
│   └── sync.py                  BulkUpload + files + row errors
├── services/
│   └── auth_service.py          login / mfa / invite issuance + consumption
├── templates/
│   ├── _base.html               HTML skeleton + Tailwind/HTMX/Alpine CDN
│   ├── _shell.html              authenticated app shell (sidebar + topbar)
│   ├── auth/                    login, mfa enroll/challenge/recovery
│   ├── dashboard/               empty + active
│   └── error/                   404 / 401 / 500
└── static/                      (will hold compiled CSS later)

scripts/
└── seed.py                      dev seed (org + admin + user + invite)
```

---

## What's done in this scaffold

- ✅ Project structure + pyproject + .env.example
- ✅ Postgres-targeted SQLAlchemy 2 models for every V1 entity
- ✅ Single-table admission + episode with partial-unique-current invariant
- ✅ Practitioner + NPP support via `practitioner_type` enum
- ✅ Polymorphic `flag` table (HHAH-creatable, multi-source resolution)
- ✅ Alembic configured (env.py + script template)
- ✅ Permission strings + role bundles (V1: hhah_user / hhah_admin)
- ✅ JWT issuance + verification + cookie-based session for HTMX nav
- ✅ Auth service: login, TOTP MFA, invite issuance + 24h consume
- ✅ Audit + PHI access logging helpers
- ✅ Auth routes (login / mfa enroll / mfa challenge / mfa recovery / logout)
- ✅ Dashboard route (auto-switches empty ↔ active based on episodes)
- ✅ Jinja base layout + authenticated app shell
- ✅ Login + MFA pages (Tailwind, mobile-friendly)
- ✅ Empty + active dashboard pages
- ✅ 404 page
- ✅ Seed script

## Sprint progress

- ✅ **Sprint 0–1** — Foundation, schema, auth, app shell, login + MFA, empty dashboard
- ✅ **Sprint 2** — Bulk upload UI + sync history + per-row error inspector
- ✅ **Sprint 3** — Patient list + timeline view + Care Coordination Documents hub
- ✅ **Sprint 4** — Flags + Communication
- ✅ **Sprint 5** — Notifications + admin pages (BAA + Audit) + Profile + Settings
- ✅ **Sprint 6** — Tests, mobile responsive, a11y polish, structured logging, ops CLI

## Tests

```bash
createdb hhah_portal_test
pytest -q
```

Coverage: auth flow, permission gating (admin vs user), dashboard empty/active
switch, flag lifecycle, PHI access logging, route smoke tests for every
authenticated page.

## Ops CLI

See [docs/RUNBOOK.md](docs/RUNBOOK.md) for the full ops handbook. Quick reference:

```bash
python -m scripts.admin_cli new-org   --name "Sunrise HH" --slug sunrise
python -m scripts.admin_cli invite    --org-slug sunrise --email lisa@hh.com --role hhah_admin
python -m scripts.admin_cli list-orgs
python -m scripts.admin_cli list-users --org-slug sunrise
```

---

## Conventions

- **Tenant scoping** is via `org_id` on every domain table. Every query is filtered by the JWT's `org_id` claim — never accept `org_id` as a request param.
- **Permission gating** uses strings (`patient.view`), not role names, even though only `hhah_admin` and `hhah_user` exist today.
- **Soft delete only** — `deleted_at` column, never `DELETE`.
- **All writes** that touch domain state should flow through a workflow context server-side. The portal's own writes (e.g., session creation, audit log) are exceptions.
- **PHI access logging** is mandatory on every patient detail view and list view.
