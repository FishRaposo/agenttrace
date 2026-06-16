"""Logging configuration for the AgentTrace server, backed by shared_core (loguru)."""

from __future__ import annotations

import logging

from shared_core.logging import setup_logging as _shared_setup_logging


def setup_logging(level: int = logging.INFO) -> None:
    """Configure logging via shared_core.

    Args:
        level: Standard-library logging level (e.g. ``logging.INFO``). Converted to
            the level name shared_core expects.
    """
    level_name = logging.getLevelName(level) if isinstance(level, int) else str(level)
    _shared_setup_logging(level=level_name, service_name="agenttrace")
