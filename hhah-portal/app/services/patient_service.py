"""Patient queries — list, detail, timeline.

The portal does not WRITE patient state; the orchestrator does. The portal
reads, computes derived display fields (current episode dates, recert status),
and logs PHI access.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models.admission import Admission, Episode
from app.models.flag import Flag
from app.models.patient import Patient
from app.models.practitioner import Practitioner, PracticeOrg


@dataclass(slots=True)
class PatientRow:
    patient: Patient
    pg_name: Optional[str]
    practitioner_label: Optional[str]
    current_episode_start: Optional[date]
    current_episode_end: Optional[date]
    current_episode_day: Optional[int]
    recert_overdue: bool
    flag_count: int


def _practitioner_label(p: Optional[Practitioner]) -> Optional[str]:
    if not p:
        return None
    title = "Dr." if p.practitioner_type == "physician" else ""
    return f"{title} {p.first_name[:1]}. {p.last_name}".strip()


def list_patients(
    db: Session,
    *,
    org_id: UUID,
    q: Optional[str] = None,
    practice_org_id: Optional[UUID] = None,
    practitioner_id: Optional[UUID] = None,
    flagged_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> list[PatientRow]:
    stmt = (
        select(Patient)
        .where(Patient.org_id == org_id, Patient.deleted_at.is_(None))
    )
    if q:
        like = f"%{q}%"
        stmt = stmt.where((Patient.last_name.ilike(like)) | (Patient.first_name.ilike(like)) | (Patient.mrn.ilike(like)))
    if practice_org_id:
        stmt = stmt.where(Patient.primary_practice_org_id == practice_org_id)
    if practitioner_id:
        stmt = stmt.where(Patient.primary_practitioner_id == practitioner_id)
    stmt = stmt.order_by(Patient.last_name.asc()).limit(limit).offset(offset)

    patients = list(db.scalars(stmt))

    rows: list[PatientRow] = []
    today = datetime.now(timezone.utc).date()
    for p in patients:
        # Current episode
        ep = db.scalar(
            select(Episode)
            .where(
                Episode.patient_id == p.patient_id,
                Episode.status == "current",
                Episode.deleted_at.is_(None),
            )
        )
        # Practitioner + PG
        prac = db.get(Practitioner, p.primary_practitioner_id) if p.primary_practitioner_id else None
        pg = db.get(PracticeOrg, p.primary_practice_org_id) if p.primary_practice_org_id else None

        # Flags open count
        fl = db.scalar(
            select(func.count(Flag.id)).where(
                Flag.org_id == org_id,
                Flag.subject_type == "patient",
                Flag.subject_id == p.patient_id,
                Flag.status.in_(["open", "acknowledged", "escalated"]),
                Flag.deleted_at.is_(None),
            )
        ) or 0

        if flagged_only and fl == 0:
            continue

        ep_start = ep.start_date if ep else None
        ep_end = ep.end_date if ep else None
        ep_day = (today - ep_start).days + 1 if ep_start else None
        overdue = bool(ep_end and ep_end < today and ep.status == "current") if ep else False

        rows.append(PatientRow(
            patient=p,
            pg_name=pg.name if pg else None,
            practitioner_label=_practitioner_label(prac),
            current_episode_start=ep_start,
            current_episode_end=ep_end,
            current_episode_day=ep_day,
            recert_overdue=overdue,
            flag_count=fl,
        ))
    return rows


@dataclass(slots=True)
class PatientDetailView:
    patient: Patient
    practitioner: Optional[Practitioner]
    practice_org: Optional[PracticeOrg]
    current_admission: Optional[Admission]
    past_admissions: list[Admission]


def get_patient_detail(db: Session, *, org_id: UUID, patient_id: UUID) -> Optional[PatientDetailView]:
    p = db.scalar(
        select(Patient).where(
            Patient.patient_id == patient_id,
            Patient.org_id == org_id,
            Patient.deleted_at.is_(None),
        )
    )
    if not p:
        return None

    current = db.scalar(
        select(Admission).where(
            Admission.patient_id == patient_id,
            Admission.status == "current",
            Admission.deleted_at.is_(None),
        )
    )
    past = list(db.scalars(
        select(Admission)
        .where(
            Admission.patient_id == patient_id,
            Admission.status == "past",
            Admission.deleted_at.is_(None),
        )
        .order_by(Admission.start_date.desc())
    ))
    prac = db.get(Practitioner, p.primary_practitioner_id) if p.primary_practitioner_id else None
    pg = db.get(PracticeOrg, p.primary_practice_org_id) if p.primary_practice_org_id else None
    return PatientDetailView(
        patient=p, practitioner=prac, practice_org=pg,
        current_admission=current, past_admissions=past,
    )


def get_episodes_for_admission(db: Session, *, admission_id: UUID) -> list[Episode]:
    return list(db.scalars(
        select(Episode)
        .where(Episode.admission_id == admission_id, Episode.deleted_at.is_(None))
        .order_by(Episode.start_date.asc())
    ))
