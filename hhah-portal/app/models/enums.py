"""Domain enums — match the DDL diff verbatim."""
from __future__ import annotations

from enum import Enum


class PractitionerType(str, Enum):
    PHYSICIAN = "physician"
    NP        = "np"
    PA        = "pa"
    CNS       = "cns"
    CRNA      = "crna"
    CNM       = "cnm"
    OTHER     = "other"


class PGPractitionerRole(str, Enum):
    OWNER       = "owner"
    EMPLOYED    = "employed"
    CONTRACTED  = "contracted"
    COVERING    = "covering"


class AdmissionStatus(str, Enum):
    CURRENT   = "current"
    PAST      = "past"
    CANCELLED = "cancelled"


class EpisodeStatus(str, Enum):
    CURRENT   = "current"
    PAST      = "past"
    CLOSED    = "closed"
    CANCELLED = "cancelled"


class FlagSource(str, Enum):
    HHAH_USER    = "hhah_user"
    PG           = "pg"
    PROVIDER     = "provider"
    US           = "us"
    SYSTEM_AUTO  = "system_auto"


class FlagSubjectType(str, Enum):
    PATIENT    = "patient"
    ADMISSION  = "admission"
    EPISODE    = "episode"
    F2F        = "f2f"
    POC_485    = "plan_of_care_485"
    ORDER      = "order"


class FlagStatus(str, Enum):
    OPEN          = "open"
    ACKNOWLEDGED  = "acknowledged"
    RESOLVED      = "resolved"
    ESCALATED     = "escalated"
    DISMISSED     = "dismissed"


class FlagResolutionMethod(str, Enum):
    MARKED_RESOLVED       = "marked_resolved"
    CLOSED_BY_US          = "closed_by_us"
    CLOSED_BY_PG          = "closed_by_pg"
    CLOSED_BY_PROVIDER    = "closed_by_provider"
    AUTO_CLOSED_EVENT     = "auto_closed_event"
    DISMISSED             = "dismissed"


class FlagSeverity(str, Enum):
    LOW       = "low"
    MEDIUM    = "medium"
    HIGH      = "high"
    CRITICAL  = "critical"


class DocumentType(str, Enum):
    POC_485             = "plan_of_care_485"
    F2F                 = "f2f"
    SUPPLEMENTAL_ORDER  = "supplemental_order"
    DISCHARGE_SUMMARY   = "discharge_summary"
    HOSPITAL_DC         = "hospital_dc"
    LAB                 = "lab"
    INSURANCE           = "insurance"
    OASIS               = "oasis"
    VISIT_NOTE          = "visit_note"
    OTHER               = "other"


class SignatureRequestStatus(str, Enum):
    PENDING   = "pending"
    SIGNED    = "signed"
    EXPIRED   = "expired"
    REJECTED  = "rejected"
    CANCELLED = "cancelled"


class BulkUploadStatus(str, Enum):
    QUEUED      = "queued"
    PROCESSING  = "processing"
    COMPLETE    = "complete"
    PARTIAL     = "partial"
    FAILED      = "failed"


class UserRole(str, Enum):
    HHAH_ADMIN = "hhah_admin"
    HHAH_USER  = "hhah_user"
