"""Permission strings + role bundles. Permission-based gating, not role-based."""
from __future__ import annotations

# ─── Permission registry ─────────────────────────────────────────────
# Every gated endpoint references one of these strings.
class P:
    # Profile / sessions
    PROFILE_UPDATE       = "profile.update"
    SESSION_REVOKE       = "session.revoke"

    # Search
    SEARCH_GLOBAL        = "search.global"

    # Dashboard
    DASHBOARD_VIEW       = "dashboard.view"

    # Sync
    SYNC_VIEW            = "sync.view"
    SYNC_UPLOAD          = "sync.upload"

    # Patients
    PATIENT_VIEW         = "patient.view"

    # Documents
    DOCUMENT_VIEW        = "document.view"
    DOCUMENT_COMMENT     = "document.comment"
    DOCUMENT_BULK        = "document.bulk"

    # Signature requests (read-only on HHAH side)
    SIGREQ_VIEW          = "signature_request.view"

    # Flags
    FLAG_VIEW            = "flag.view"
    FLAG_CREATE          = "flag.create"
    FLAG_ACT             = "flag.act"
    FLAG_COMMENT         = "flag.comment"
    FLAG_BULK            = "flag.bulk"

    # Communication
    COMM_VIEW            = "communication.view"
    COMM_CREATE          = "communication.create"
    COMM_SEND            = "communication.send"
    COMM_READ            = "communication.read"

    # Notifications
    NOTIF_VIEW           = "notification.view"
    NOTIF_ACT            = "notification.act"

    # Admin only
    BAA_VIEW             = "baa.view"
    AUDIT_VIEW           = "audit.view"


# ─── Role bundles ────────────────────────────────────────────────────
HHAH_USER_PERMS: list[str] = [
    P.PROFILE_UPDATE, P.SESSION_REVOKE,
    P.SEARCH_GLOBAL, P.DASHBOARD_VIEW,
    P.SYNC_VIEW, P.SYNC_UPLOAD,
    P.PATIENT_VIEW,
    P.DOCUMENT_VIEW, P.DOCUMENT_COMMENT, P.DOCUMENT_BULK,
    P.SIGREQ_VIEW,
    P.FLAG_VIEW, P.FLAG_CREATE, P.FLAG_ACT, P.FLAG_COMMENT, P.FLAG_BULK,
    P.COMM_VIEW, P.COMM_CREATE, P.COMM_SEND, P.COMM_READ,
    P.NOTIF_VIEW, P.NOTIF_ACT,
]

HHAH_ADMIN_PERMS: list[str] = HHAH_USER_PERMS + [
    P.BAA_VIEW,
    P.AUDIT_VIEW,
]

ROLE_PERMISSIONS: dict[str, list[str]] = {
    "hhah_user":  HHAH_USER_PERMS,
    "hhah_admin": HHAH_ADMIN_PERMS,
}


def permissions_for(role: str) -> list[str]:
    return ROLE_PERMISSIONS.get(role, [])
