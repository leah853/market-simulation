"""Shared Jinja templating + HTMX helpers."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from fastapi import Request
from fastapi.templating import Jinja2Templates
from starlette.responses import HTMLResponse

from app.core.deps import CurrentUser, get_current_user_optional

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def is_htmx(request: Request) -> bool:
    return request.headers.get("HX-Request") == "true"


def render(
    request: Request,
    template: str,
    context: Optional[dict[str, Any]] = None,
    *,
    user: Optional[CurrentUser] = None,
    status_code: int = 200,
) -> HTMLResponse:
    """Render a template with shared globals (current user, brand, request)."""
    ctx: dict[str, Any] = {
        "request": request,
        "user": user,
        "is_htmx": is_htmx(request),
    }
    if context:
        ctx.update(context)
    return templates.TemplateResponse(template, ctx, status_code=status_code)
