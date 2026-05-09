"""FastAPI app entrypoint."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import admin as admin_routes
from app.api.routes import auth as auth_routes
from app.api.routes import care_docs as care_docs_routes
from app.api.routes import communication as communication_routes
from app.api.routes import dashboard as dashboard_routes
from app.api.routes import flags as flags_routes
from app.api.routes import notifications as notifications_routes
from app.api.routes import patients as patients_routes
from app.api.routes import profile as profile_routes
from app.api.routes import sync as sync_routes
from app.api.templating import render
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware

configure_logging()
settings = get_settings()

app = FastAPI(
    title="Eonexea HHAH Portal",
    version="0.1.0",
    debug=settings.app_debug,
    docs_url="/_docs" if settings.app_env != "production" else None,
    redoc_url=None,
)

# Middleware
app.add_middleware(RequestContextMiddleware)

# Static
STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Routes
app.include_router(auth_routes.router, tags=["auth"])
app.include_router(dashboard_routes.router, tags=["dashboard"])
app.include_router(sync_routes.router, tags=["sync"])
app.include_router(patients_routes.router, tags=["patients"])
app.include_router(care_docs_routes.router, tags=["care-docs"])
app.include_router(flags_routes.router, tags=["flags"])
app.include_router(communication_routes.router, tags=["communication"])
app.include_router(notifications_routes.router, tags=["notifications"])
app.include_router(profile_routes.router, tags=["profile"])
app.include_router(admin_routes.router, tags=["admin"])


# Friendly error pages
@app.exception_handler(404)
async def not_found(request: Request, exc):
    return render(request, "error/404.html",
                  {"app_brand": settings.app_brand}, status_code=404)


@app.exception_handler(401)
async def unauthorized(request: Request, exc):
    # Auth-required redirects to login for HTML requests
    if "text/html" in request.headers.get("accept", ""):
        return RedirectResponse(url="/login", status_code=303)
    return HTMLResponse(content='{"error":{"code":"unauthorized"}}', status_code=401,
                        media_type="application/json")


@app.get("/healthz")
def health():
    return {"status": "ok", "env": settings.app_env}
