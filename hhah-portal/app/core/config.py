"""Application configuration loaded from environment."""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_env: Literal["local", "staging", "production"] = "local"
    app_debug: bool = True
    app_base_url: str = "http://localhost:8000"
    app_brand: str = "Eonexea"

    # Database
    database_url: str = "postgresql+psycopg://hhah:hhah@localhost:5432/hhah_portal"

    # Auth
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_ttl_seconds: int = 900            # 15 min
    jwt_refresh_ttl_seconds: int = 60 * 60 * 24 * 7  # 7 days

    session_idle_minutes: int = 15
    session_absolute_hours: int = 12
    session_concurrent_limit: int = 3

    # SSO
    sso_doximity_client_id: str = ""
    sso_doximity_client_secret: str = ""
    sso_microsoft_client_id: str = ""
    sso_microsoft_client_secret: str = ""
    sso_google_client_id: str = ""
    sso_google_client_secret: str = ""

    # Storage
    s3_bucket: str = "hhah-portal-dev"
    aws_region: str = "us-west-2"

    # Misc
    invite_link_ttl_hours: int = 24
    phi_log_retention_years: int = 6


@lru_cache
def get_settings() -> Settings:
    return Settings()
