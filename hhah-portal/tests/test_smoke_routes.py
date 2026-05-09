"""Smoke test — every authenticated route returns 2xx for an admin user."""
import pytest


@pytest.mark.parametrize("path", [
    "/",
    "/sync",
    "/sync/upload",
    "/sync/uploads",
    "/patients",
    "/care-docs",
    "/care-docs/signature-required",
    "/care-docs/other",
    "/flags",
    "/communication",
    "/communication/new",
    "/notifications",
    "/profile",
    "/settings",
    "/admin/baa",
    "/admin/audit",
])
def test_admin_smoke(authed_client, path):
    r = authed_client.get(path, follow_redirects=True)
    assert r.status_code == 200, f"{path} returned {r.status_code}"


@pytest.mark.parametrize("path", [
    "/", "/sync", "/sync/upload", "/patients",
    "/care-docs/signature-required", "/care-docs/other",
    "/flags", "/communication", "/notifications", "/profile", "/settings",
])
def test_hhah_user_smoke(authed_user_client, path):
    r = authed_user_client.get(path, follow_redirects=True)
    assert r.status_code == 200, f"{path} returned {r.status_code}"
