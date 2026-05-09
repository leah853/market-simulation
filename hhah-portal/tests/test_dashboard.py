"""Dashboard auto-switches between empty and active based on episode count."""
from __future__ import annotations

from datetime import date, timedelta
from uuid import uuid4

from app.models.admission import Admission, Episode
from app.models.patient import Patient


def test_dashboard_empty_state_when_no_episodes(authed_client):
    r = authed_client.get("/")
    assert r.status_code == 200
    assert "Coming soon" in r.text or "coming soon" in r.text


def test_dashboard_switches_to_active_after_first_episode(db, authed_client, admin_user):
    p = Patient(
        org_id=admin_user.org_id, mrn="TEST-001",
        first_name="Test", last_name="Patient",
        dob=date(1950, 1, 1),
    )
    db.add(p); db.flush()
    a = Admission(
        org_id=admin_user.org_id, patient_id=p.patient_id,
        status="current", start_date=date.today() - timedelta(days=10),
    )
    db.add(a); db.flush()
    e = Episode(
        org_id=admin_user.org_id, admission_id=a.id, patient_id=p.patient_id,
        status="current", episode_number=1,
        start_date=date.today() - timedelta(days=10),
        end_date=date.today() + timedelta(days=50),
    )
    db.add(e); db.commit()

    r = authed_client.get("/")
    assert r.status_code == 200
    assert "Coming soon" not in r.text
    assert "Active Patients" in r.text
