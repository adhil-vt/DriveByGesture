"""
gesturedrive.core.logger
=========================
Centralized Production Logging System for DriveByGesture.

Features
--------
- Daily rotating log files in logs/ directory (logs/YYYY-MM-DD.log).
- Configurable log retention backup count (default: 14 days).
- Precise timestamps, thread names, module, function name, and line numbers.
- Integration with GUILogHandler for live Qt log viewer.
"""

from __future__ import annotations

import datetime
import logging
from logging.handlers import TimedRotatingFileHandler
import os
from pathlib import Path
import sys
from typing import List, Optional

from core.resources import get_base_dir, get_user_crash_reports_dir, get_user_logs_dir
from gui.logger import GUILogHandler

_LOGGER_INITIALIZED = False
_ACTIVE_LOG_FILE: Optional[Path] = None


def get_log_dir() -> Path:
    """Return Path to logs/ directory in user-writable local app data."""
    return get_user_logs_dir()


def get_crash_reports_dir() -> Path:
    """Return Path to crash_reports/ directory in user-writable local app data."""
    return get_user_crash_reports_dir()


def setup_central_logging(
    level: int = logging.INFO,
    backup_count: int = 14,
) -> logging.Logger:
    """
    Initialize central production logging with daily file rotation and GUI emitter.
    """
    global _LOGGER_INITIALIZED, _ACTIVE_LOG_FILE
    root_logger = logging.getLogger()

    if _LOGGER_INITIALIZED:
        return root_logger

    root_logger.setLevel(level)

    log_dir = get_log_dir()
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    _ACTIVE_LOG_FILE = log_dir / f"{today_str}.log"

    # Precise log formatter
    fmt = logging.Formatter(
        "[%(asctime)s.%(msecs)03d] [%(levelname)-7s] [%(threadName)s] [%(name)s.%(funcName)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 1. Daily Rotating File Handler
    file_handler = TimedRotatingFileHandler(
        filename=str(_ACTIVE_LOG_FILE),
        when="midnight",
        interval=1,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(fmt)
    root_logger.addHandler(file_handler)

    # 2. Console Handler (stdout)
    console_fmt = logging.Formatter("[%(asctime)s] [%(levelname)s] %(name)s: %(message)s", "%H:%M:%S")
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(console_fmt)
    root_logger.addHandler(console_handler)

    # 3. GUI Handler for Live Log Viewer
    gui_handler = GUILogHandler(level)
    root_logger.addHandler(gui_handler)

    _LOGGER_INITIALIZED = True
    logging.info("Centralized logging system initialized. Active log: %s", _ACTIVE_LOG_FILE)
    return root_logger


def get_recent_logs(max_entries: int = 100) -> List[str]:
    """Read and return recent log lines from current active log file."""
    if not _ACTIVE_LOG_FILE or not _ACTIVE_LOG_FILE.exists():
        # Fallback to newest log file in logs/
        log_dir = get_log_dir()
        log_files = sorted(log_dir.glob("*.log"), key=os.path.getmtime, reverse=True)
        if not log_files:
            return []
        target = log_files[0]
    else:
        target = _ACTIVE_LOG_FILE

    try:
        lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
        return lines[-max_entries:]
    except Exception as exc:
        logging.warning("Could not read recent logs: %s", exc)
        return []
