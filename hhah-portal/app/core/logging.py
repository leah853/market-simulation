"""Structured logging via structlog. JSON in non-local envs, human-readable locally."""
from __future__ import annotations

import logging
import sys

import structlog

from app.core.config import get_settings


def configure_logging() -> None:
    s = get_settings()

    processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
    ]
    if s.app_env == "local":
        processors.append(structlog.dev.ConsoleRenderer(colors=False))
    else:
        processors.append(structlog.processors.JSONRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.DEBUG if s.app_debug else logging.INFO
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "hhah") -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
