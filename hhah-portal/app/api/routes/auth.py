"""Auth routes — login, invite-accept, MFA enrol/challenge, logout.

Two flavours of routes here:
  - HTML page routes that render Jinja (login form, MFA challenge)
  - JSON API equivalents under /api/v1/* for programmatic clients
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, Form, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.api.templating import render
from app.core.config import get_settings
from app.core.deps import CurrentUser, get_current_user, get_current_user_optional
from app.db.session import get_db
from app.services import auth_service as auth

router = APIRouter()


# ─── Login (page + form post) ───────────────────────────────────────

@router.get("/login", response_class=None, name="login_page")
def login_page(request: Request,
               user: Optional[CurrentUser] = Depends(get_current_user_optional)):
    if user and user.mfa_verified:
        return Response(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/"})
    return render(request, "auth/login.html", {"app_brand": get_settings().app_brand},
                  user=user)


@router.post("/login")
def login_submit(
    request: Request,
    response: Response,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    try:
        user = auth.authenticate(db, email=email, password=password)
    except auth.AuthError:
        return render(
            request, "auth/login.html",
            {"error": "Invalid email or password.",
             "email": email,
             "app_brand": get_settings().app_brand},
            status_code=400,
        )

    # MFA required? If not enrolled yet, route to enrollment; else challenge.
    needs_mfa_enroll = not user.mfa_totp_enrolled and not user.mfa_webauthn_enrolled
    access, refresh, _sess = auth.issue_session(
        db, user=user, mfa_verified=False,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.commit()

    redirect_to = "/auth/mfa/enroll" if needs_mfa_enroll else "/auth/mfa/challenge"
    resp = Response(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": redirect_to})
    _set_session_cookies(resp, access, refresh)
    return resp


# ─── MFA enrollment + challenge ─────────────────────────────────────

@router.get("/auth/mfa/enroll")
def mfa_enroll_page(request: Request, db: Session = Depends(get_db),
                    user: Optional[CurrentUser] = Depends(get_current_user_optional)):
    if not user:
        return Response(status_code=303, headers={"Location": "/login"})
    from app.models.user import User as UserModel
    db_user = db.get(UserModel, user.user_id)
    secret, uri = auth.begin_totp_enrollment(db, db_user)
    db.commit()
    return render(request, "auth/mfa_enroll.html",
                  {"otpauth_uri": uri, "secret": secret,
                   "app_brand": get_settings().app_brand},
                  user=user)


@router.post("/auth/mfa/enroll")
def mfa_enroll_submit(
    request: Request,
    code: str = Form(...),
    db: Session = Depends(get_db),
    user: Optional[CurrentUser] = Depends(get_current_user_optional),
):
    if not user:
        return Response(status_code=303, headers={"Location": "/login"})
    from app.models.user import User as UserModel
    db_user = db.get(UserModel, user.user_id)
    try:
        recovery = auth.confirm_totp_enrollment(db, db_user, code)
    except auth.AuthError:
        return render(request, "auth/mfa_enroll.html",
                      {"error": "Invalid code. Try again.",
                       "app_brand": get_settings().app_brand},
                      status_code=400, user=user)
    # Re-issue tokens with mfa_verified=true
    access, refresh, _ = auth.issue_session(
        db, user=db_user, mfa_verified=True,
    )
    db.commit()
    resp = render(request, "auth/mfa_recovery.html",
                  {"recovery_codes": recovery,
                   "app_brand": get_settings().app_brand}, user=user)
    _set_session_cookies(resp, access, refresh)
    return resp


@router.get("/auth/mfa/challenge")
def mfa_challenge_page(request: Request,
                       user: Optional[CurrentUser] = Depends(get_current_user_optional)):
    if not user:
        return Response(status_code=303, headers={"Location": "/login"})
    return render(request, "auth/mfa_challenge.html",
                  {"app_brand": get_settings().app_brand}, user=user)


@router.post("/auth/mfa/challenge")
def mfa_challenge_submit(
    request: Request,
    code: str = Form(...),
    db: Session = Depends(get_db),
    user: Optional[CurrentUser] = Depends(get_current_user_optional),
):
    if not user:
        return Response(status_code=303, headers={"Location": "/login"})
    from app.models.user import User as UserModel
    db_user = db.get(UserModel, user.user_id)
    if not auth.verify_totp(db_user, code):
        return render(request, "auth/mfa_challenge.html",
                      {"error": "Invalid code.",
                       "app_brand": get_settings().app_brand},
                      status_code=400, user=user)
    access, refresh, _ = auth.issue_session(db, user=db_user, mfa_verified=True)
    db.commit()
    resp = Response(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/"})
    _set_session_cookies(resp, access, refresh)
    return resp


# ─── Logout ─────────────────────────────────────────────────────────

@router.post("/logout")
def logout():
    resp = Response(status_code=303, headers={"Location": "/login"})
    resp.delete_cookie("access_token", path="/")
    resp.delete_cookie("refresh_token", path="/")
    return resp


# ─── Helpers ────────────────────────────────────────────────────────

def _set_session_cookies(resp: Response, access: str, refresh: str) -> None:
    s = get_settings()
    secure = s.app_env != "local"
    resp.set_cookie(
        "access_token", access, httponly=True, secure=secure, samesite="lax",
        max_age=s.jwt_access_ttl_seconds, path="/",
    )
    resp.set_cookie(
        "refresh_token", refresh, httponly=True, secure=secure, samesite="lax",
        max_age=s.jwt_refresh_ttl_seconds, path="/",
    )
