"""
gesturedrive.core.crash_handler
================================
Global Crash Recovery and Diagnostic Report Generation System.

Hooks into sys.excepthook and threading.excepthook to intercept unhandled
exceptions, write structured crash reports to crash_reports/, and launch CrashDialog.
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import platform
import sys
import threading
import traceback
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

from core.logger import get_crash_reports_dir, get_recent_logs
from core.version import APP_NAME, BUILD_NUMBER, RELEASE_CHANNEL, VERSION

logger = logging.getLogger(__name__)

_CRASH_HANDLER_INSTALLED = False


def generate_crash_report(
    exc_type,
    exc_value,
    exc_traceback,
    active_profile: str = "Default",
    active_settings: Optional[dict] = None,
) -> Path:
    """
    Generate structured crash report file in crash_reports/ directory.
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    filename_ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    tb_str = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))

    py_ver = sys.version.split(" ")[0]
    pyside_ver = "N/A"
    cv_ver = "N/A"
    mp_ver = "N/A"

    try:
        import PySide6
        pyside_ver = PySide6.__version__
    except Exception:
        pass
    try:
        import cv2
        cv_ver = cv2.__version__
    except Exception:
        pass
    try:
        import mediapipe as mp
        mp_ver = getattr(mp, "__version__", "0.10.x")
    except Exception:
        pass

    report_data = {
        "timestamp": timestamp,
        "application": {
            "name": APP_NAME,
            "version": VERSION,
            "build_number": BUILD_NUMBER,
            "release_channel": RELEASE_CHANNEL,
        },
        "environment": {
            "operating_system": f"{platform.system()} {platform.release()} ({platform.machine()})",
            "python_version": py_ver,
            "pyside6_version": pyside_ver,
            "opencv_version": cv_ver,
            "mediapipe_version": mp_ver,
        },
        "exception_type": getattr(exc_type, "__name__", str(exc_type)),
        "exception_message": str(exc_value),
        "stack_trace": tb_str,
        "active_profile": active_profile,
        "active_settings": active_settings or {},
        "recent_logs": get_recent_logs(100),
    }

    crash_dir = get_crash_reports_dir()
    report_file = crash_dir / f"crash_{filename_ts}.json"

    try:
        report_file.write_text(json.dumps(report_data, indent=2), encoding="utf-8")
        logger.info("Crash report generated successfully: %s", report_file)
    except Exception as exc:
        logger.error("Failed to write crash report file: %s", exc)

    return report_file, report_data


def global_exception_hook(exc_type, exc_value, exc_traceback) -> None:
    """Global sys.excepthook handler for catching unhandled exceptions."""
    if issubclass(exc_type, KeyboardInterrupt) or issubclass(exc_type, SystemExit):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logger.critical("Unhandled exception intercepted!", exc_info=(exc_type, exc_value, exc_traceback))

    report_file, report_data = generate_crash_report(exc_type, exc_value, exc_traceback)

    # Launch CrashDialog if Qt application is running
    app = QApplication.instance()
    if app is not None:
        try:
            from gui.crash_dialog import CrashDialog
            dialog = CrashDialog(report_file, report_data)
            dialog.exec()
        except Exception as exc:
            logger.error("Failed to launch CrashDialog: %s", exc)


def threading_exception_hook(args) -> None:
    """Thread exception hook for catching unhandled worker thread crashes."""
    logger.critical("Worker thread exception in %s!", args.thread.name, exc_info=(args.exc_type, args.exc_value, args.exc_traceback))
    global_exception_hook(args.exc_type, args.exc_value, args.exc_traceback)


def install_global_crash_handler() -> None:
    """Install sys.excepthook and threading.excepthook handlers."""
    global _CRASH_HANDLER_INSTALLED
    if _CRASH_HANDLER_INSTALLED:
        return

    sys.excepthook = global_exception_hook
    if hasattr(threading, "excepthook"):
        threading.excepthook = threading_exception_hook

    _CRASH_HANDLER_INSTALLED = True
    logger.info("Global crash handler installed.")
