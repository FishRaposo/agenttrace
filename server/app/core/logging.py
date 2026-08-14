"""Logging configuration for the AgentTrace server."""

from __future__ import annotations

import logging

from app.internal.vendor_core.logging import setup_logging as _vendor_setup_logging


def setup_logging(level: int = logging.INFO) -> None:
    """Configure logging via the internally vendored logging implementation.

    Args:
        level: Standard-library logging level (e.g. ``logging.INFO``). Converted to
            the level name the vendor implementation expects.
    """
    level_name = logging.getLevelName(level) if isinstance(level, int) else str(level)
    _vendor_setup_logging(level=level_name, service_name="agenttrace")
