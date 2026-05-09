"""Flag lifecycle — create, acknowledge, resolve."""
from __future__ import annotations

from datetime import date
from uuid import uuid4

from sqlalchemy import select

from app.models.flag import Flag
from app.models.patient import Patient
from app.services import flag_service as fs


def _make_patient(db, org):
    p = Patient(
        org_id=org.id, mrn=f"MRN-{uuid4().hex[:6]}",
        first_name="Jane", last_name="Doe", dob=date(1948, 3, 14),
    )
    db.add(p); db.commit()
    return p


def test_user_can_create_flag(db, hhah_user, org):
    p = _make_patient(db, org)
    f = fs.create_flag(
        db, org_id=org.id, user_id=hhah_user.id,
        subject_type="patient", subject_id=p.patient_id,
        category="missing_doc", severity="high",
        reason="Missing F2F for upcoming recert",
    )
    db.commit()
    assert f.id is not None
    assert f.source == "hhah_user"
    assert f.status == "open"


def test_acknowledge_then_resolve_flag(db, hhah_user, org):
    p = _make_patient(db, org)
    f = fs.create_flag(
        db, org_id=org.id, user_id=hhah_user.id,
        subject_type="patient", subject_id=p.patient_id,
        category="other", severity="medium",
        reason="test reason",
    )
    db.commit()

    fs.acknowledge(db, org_id=org.id, user_id=hhah_user.id, flag_id=f.id)
    db.commit()
    assert f.status == "acknowledged"
    assert f.acknowledged_at is not None

    fs.resolve(db, org_id=org.id, user_id=hhah_user.id,
               flag_id=f.id, notes="all clear")
    db.commit()
    assert f.status == "resolved"
    assert f.resolved_at is not None
    assert f.resolution_method == "marked_resolved"


def test_summary_counts(db, hhah_user, org):
    p = _make_patient(db, org)
    for sev in ("low", "high"):
        fs.create_flag(
            db, org_id=org.id, user_id=hhah_user.id,
            subject_type="patient", subject_id=p.patient_id,
            category="other", severity=sev, reason="x",
        )
    db.commit()

    s = fs.summarize(db, org_id=org.id)
    assert s.open == 2


def test_create_flag_via_form(db, authed_client, admin_user, org):
    p = _make_patient(db, org)
    r = authed_client.post(
        "/flags/new",
        data={
            "subject_type": "patient",
            "subject_id":   str(p.patient_id),
            "category":     "missing_doc",
            "severity":     "high",
            "reason":       "via web form",
        },
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert r.headers["location"] == "/flags"

    rows = list(db.scalars(select(Flag).where(Flag.org_id == org.id)))
    assert any(f.reason == "via web form" for f in rows)
