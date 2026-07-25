"""
gesturedrive.logging_system.formatters
========================================
Custom log formatters for GestureDrive.

JsonFormatter
-------------
Emits each log record as a single-line JSON object.
Fields: timestamp, level, logger, message, [exc_info].
Suitable for log aggregation pipelines (e.g., Loki, Splunk, ELK).

ColorConsoleFormatter
---------------------
ANSI-colored console output for development.
Colors: DEBUG=cyan, INFO=green, WARNING=yellow, ERROR=red, CRITICAL=magenta.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    """
    Formats log records as single-line JSON for machine consumption.

    Each line is a valid JSON object with the following fields:
    - ``ts``:      ISO 8601 UTC timestamp
    - ``level``:   Log level name
    - ``logger``:  Logger name (dotted module path)
    - ``msg``:     Formatted message string
    - ``exc``:     Exception info string (only present when an exception exists)
    """

    def format(self, record: logging.LogRecord) -> str:  # noqa: A003
        payload = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


class ColorConsoleFormatter(logging.Formatter):
    """
    ANSI-colored formatter for development console output.

    Falls back gracefully on terminals that don't support ANSI codes.
    """

    _COLORS = {
        "DEBUG":    "\033[36m",    # cyan
        "INFO":     "\033[32m",    # green
        "WARNING":  "\033[33m",    # yellow
        "ERROR":    "\033[31m",    # red
        "CRITICAL": "\033[35m",    # magenta
    }
    _RESET = "\033[0m"

    _FMT = "{color}[{levelname:<8}]{reset} {asctime} | {name} | {message}"

    def format(self, record: logging.LogRecord) -> str:  # noqa: A003
        color = self._COLORS.get(record.levelname, "")
        formatter = logging.Formatter(
            fmt=self._FMT.format(
                color=color,
                levelname=record.levelname,
                reset=self._RESET,
                asctime="%(asctime)s",
                name="%(name)s",
                message="%(message)s",
            ),
            datefmt="%H:%M:%S",
            style="%",
        )
        return formatter.format(record)
