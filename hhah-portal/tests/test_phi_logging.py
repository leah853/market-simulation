"""PHI access log is written on patient list + detail views."""
from __future__ import annotations

from datetime import date
from uuid import uuid4

from sqlalchemy import select

from app.models.audit import PHIAccessLog
from app.models.patient import Patient


def test_phi_log_written_on_patient_list(db, authed_client, org):
    r = authed_client.get("/patients")
    assert r.status_code == 200

    logs = list(db.scalars(select(PHIAccessLog).where(PHIAccessLog.org_id == org.id)))
    assert any(l.access_granularity == "query" for l in logs)


def test_phi_log_written_on_patient_detail(db, authed_client, org):
    p = Patient(
        org_id=org.id, mrn=f"MRN-{uuid4().hex[:6]}",
        first_name="John", last_name="Doe", dob=date(1948, 3, 14),
    )
    db.add(p); db.commit()

    r = authed_client.get(f"/patients/{p.patient_id}")
    assert r.status_code == 200

    logs = list(db.scalars(
        select(PHIAccessLog).where(
            PHIAccessLog.org_id == org.id,
            PHIAccessLog.patient_id == p.patient_id,
        )
    ))
    assert any(l.access_granularity == "row_expand" for l in logs)
