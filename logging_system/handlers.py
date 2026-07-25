"""
gesturedrive.logging_system.handlers
========================================
Pre-configured log handler factory functions.

These are called by LoggerFactory.configure() to attach handlers to the
root gesturedrive logger. Kept separate to allow handler configuration
to be changed without touching LoggerFactory.
"""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path
from typing import Optional

from logging_system.formatters import ColorConsoleFormatter, JsonFormatter


def make_console_handler(level: str = "DEBUG") -> logging.StreamHandler:
    """
    Create a colored console handler for development output.

    Parameters
    ----------
    level:
        Minimum log level to emit to the console.

    Returns
    -------
    logging.StreamHandler
        A handler writing to sys.stderr with ColorConsoleFormatter.
    """
    handler = logging.StreamHandler()
    handler.setLevel(level)
    handler.setFormatter(ColorConsoleFormatter())
    return handler


def make_file_handler(
    log_path: Path,
    max_bytes: int = 10_485_760,
    backup_count: int = 5,
    json_format: bool = True,
    level: str = "DEBUG",
) -> logging.handlers.RotatingFileHandler:
    """
    Create a rotating file handler.

    Parameters
    ----------
    log_path:
        Absolute path to the log file. Parent directory is created if needed.
    max_bytes:
        Maximum file size before rotation (bytes). Default 10 MB.
    backup_count:
        Number of backup files to keep.
    json_format:
        If True, use JsonFormatter; otherwise use a plain text formatter.
    level:
        Minimum log level to write to the file.

    Returns
    -------
    logging.handlers.RotatingFileHandler
    """
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.handlers.RotatingFileHandler(
        filename=str(log_path),
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    handler.setLevel(level)
    handler.setFormatter(
        JsonFormatter() if json_format else logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )
    return handler
