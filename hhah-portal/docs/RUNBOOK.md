# HHAH Portal — Operations Runbook

## Local development

```bash
# 1. Python env
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# 2. Postgres
createdb hhah_portal
createdb hhah_portal_test          # for pytest
cp .env.example .env

# 3. Migrations
alembic revision --autogenerate -m "init schema"
alembic upgrade head

# 4. Seed dev data
python -m scripts.seed

# 5. Run
uvicorn app.main:app --reload --port 8000

# 6. Tests
pytest -q
```

---

## Eonexea ops CLI

Provision a new HHAH customer:

```bash
# Step 1 — create the org
python -m scripts.admin_cli new-org --name "Sunrise Home Health" --slug sunrise

# Step 2 — invite the first admin (24h single-use link)
python -m scripts.admin_cli invite --org-slug sunrise \
                                   --email lisa@sunrisehh.com \
                                   --role hhah_admin

# (output prints the invite URL — paste into the welcome email)

# Step 3 — verify
python -m scripts.admin_cli list-orgs
python -m scripts.admin_cli list-users --org-slug sunrise
```

---

## Common operational tasks

### Reset a user's MFA
A user lost their authenticator and recovery codes. From psql:
```sql
UPDATE app_user
SET mfa_totp_enrolled = false,
    mfa_totp_secret = NULL,
    mfa_recovery_codes_hashed = NULL
WHERE email = 'user@hhah.com';
```
The user's next login will be re-routed through MFA enrollment.

### Revoke all sessions for a user
```sql
UPDATE app_session SET revoked_at = now()
WHERE user_id = '<uuid>';
```

### Suspend a user
```sql
UPDATE app_user SET is_active = false WHERE email = 'x@hhah.com';
```

### Re-issue an expired invite
```bash
python -m scripts.admin_cli invite --org-slug sunrise \
                                   --email name@hhah.com \
                                   --role hhah_user
```

---

## Observability

Every request emits a structured log line:

```json
{
  "event": "request.completed",
  "level": "info",
  "request_id": "abc123…",
  "method": "GET",
  "path": "/patients",
  "status_code": 200,
  "duration_ms": 47.3,
  "timestamp": "2026-05-09T14:22:01Z"
}
```

The same `request_id` is set as the `X-Request-Id` response header so issues
reported by users can be matched to log entries.

---

## DR / backup

- Postgres point-in-time recovery enabled
- Daily snapshots, 30-day retention
- Multi-AZ primary, async read replicas
- RPO ≤ 1 hour, RTO ≤ 4 hours (V1 targets — tightening to 5 min / 1 hr post-pilot)

Quarterly drill: restore from snapshot to a sandbox cluster, smoke-test the app.

---

## Health probe

`GET /healthz` — returns `{ "status": "ok", "env": "..." }`. Use for load
balancer health checks.

---

## Audit + PHI logs

- `audit_log` — every privileged action (login, flag create, document comment,
  profile update, BAA view, etc.)
- `phi_access_log` — every patient list view + detail view + export

Both are append-only. Retention: 6 years (HIPAA minimum).
