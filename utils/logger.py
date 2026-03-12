"""
Structured Logging Module
Provides JSON-formatted file logging with daily rotation and plain-text console output.
"""

import json
import logging
import os
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler

from utils.config import APP_LOG_DIR, LOG_LEVEL, LOG_ROTATION_DAYS


class JSONFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0] is not None:
            entry["exception"] = self.formatException(record.exc_info)
        # Attach any extra fields passed via `extra={"data": {...}}`
        if hasattr(record, "data"):
            entry["data"] = record.data
        return json.dumps(entry, default=str)


def setup_logger(name: str) -> logging.Logger:
    """
    Return a logger that writes JSON to a daily-rotated file and plain text
    to the console.  Safe to call multiple times with the same *name* — handlers
    are only added once.
    """
    logger = logging.getLogger(name)

    # Avoid duplicate handlers on repeat calls
    if logger.handlers:
        return logger

    level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(level)

    # ── File handler (JSON, daily rotation) ────────────────────────
    today = datetime.now().strftime("%Y-%m-%d")
    log_dir = os.path.join(APP_LOG_DIR, today)
    os.makedirs(log_dir, exist_ok=True)

    log_path = os.path.join(log_dir, "app.log")
    file_handler = TimedRotatingFileHandler(
        log_path,
        when="midnight",
        backupCount=LOG_ROTATION_DAYS,
        encoding="utf-8",
    )
    file_handler.setFormatter(JSONFormatter())
    file_handler.setLevel(level)
    logger.addHandler(file_handler)

    # ── Console handler (plain text) ───────────────────────────────
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter("%(asctime)s  %(levelname)-8s  %(name)s  %(message)s"))
    console.setLevel(level)
    logger.addHandler(console)

    return logger
