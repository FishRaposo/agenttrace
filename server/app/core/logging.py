from __future__ import annotations

import json
import logging
import sys
from typing import Any

from app.config import settings


class JSONFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj: dict[str, Any] = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "trace_id"):
            log_obj["trace_id"] = record.trace_id
        if hasattr(record, "run_id"):
            log_obj["run_id"] = record.run_id
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)


def setup_logging(level: int = logging.INFO) -> None:
    """Configure logging with JSON output in production."""
    is_dev = settings.ENVIRONMENT == "development"
    handler = logging.StreamHandler(sys.stdout)
    if is_dev:
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
    else:
        handler.setFormatter(JSONFormatter())

    logging.basicConfig(
        level=level,
        handlers=[handler],
    )
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
