"""Permission gating — admin sees BAA + Audit, hhah_user gets 404."""


def test_unauthenticated_redirects_to_login(client):
    r = client.get("/", follow_redirects=False)
    assert r.status_code in (303, 401)


def test_admin_can_view_baa(authed_client):
    r = authed_client.get("/admin/baa")
    assert r.status_code == 200
    assert "Business Associate Agreement" in r.text


def test_admin_can_view_audit(authed_client):
    r = authed_client.get("/admin/audit")
    assert r.status_code == 200
    assert "Audit Activity" in r.text


def test_hhah_user_blocked_from_baa(authed_user_client):
    r = authed_user_client.get("/admin/baa")
    # Permission denied — should be 403 from require_permissions, but the
    # exception handler converts to a friendly response.
    assert r.status_code in (403, 404)


def test_hhah_user_blocked_from_audit(authed_user_client):
    r = authed_user_client.get("/admin/audit")
    assert r.status_code in (403, 404)


def test_hhah_user_can_view_dashboard(authed_user_client):
    r = authed_user_client.get("/")
    assert r.status_code == 200


def test_hhah_user_can_view_patients(authed_user_client):
    r = authed_user_client.get("/patients")
    assert r.status_code == 200


def test_hhah_user_can_view_care_docs(authed_user_client):
    r = authed_user_client.get("/care-docs/signature-required")
    assert r.status_code == 200


def test_hhah_user_can_view_flags(authed_user_client):
    r = authed_user_client.get("/flags")
    assert r.status_code == 200
