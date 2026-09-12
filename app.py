"""
gesturedrive.app
=================
DriveByGesture Desktop GUI Application Entry Point (PySide6).
"""

from __future__ import annotations

import logging
import sys

from PySide6.QtWidgets import QApplication

from core.crash_handler import install_global_crash_handler
from core.logger import setup_central_logging
from core.protocol import (
    check_or_create_single_instance,
    register_url_protocol,
    unregister_url_protocol,
    validate_protocol_url,
)
from core.resources import apply_app_icon, ensure_user_data_migrated, get_app_icon
from core.version import APP_NAME, COMPANY
from gui.main_window import MainWindow
from gui.splash_screen import DriveByGestureSplashScreen

# Ensure per-user writable data directory & seed defaults (%LOCALAPPDATA%\DriveByGesture)
ensure_user_data_migrated()

# Initialize production logging system & crash recovery handler
setup_central_logging(logging.INFO)
install_global_crash_handler()


def main() -> int:
    """
    Main entry point for launching the DriveByGesture PySide6 Desktop GUI application.
    """
    # ── CLI Flag: Protocol unregistration / cleanup ───────────────────────────
    if "--unregister-protocol" in sys.argv:
        success = unregister_url_protocol()
        if sys.stdout:
            print(f"Protocol unregistration: {'SUCCESS' if success else 'FAILED'}")
        return 0 if success else 1

    # ── Protocol URL validation and argument sanitization ───────────────────
    # Ensure protocol URL strings are strictly validated and never passed
    # into the UI or application components as visible content.
    sanitized_argv = [sys.argv[0]]
    for arg in sys.argv[1:]:
        if arg.lower().startswith("rageware-gesture-drive:"):
            if not validate_protocol_url(arg):
                logging.getLogger(__name__).warning("Ignored invalid or unsafe protocol URL: %s", arg)
            continue
        sanitized_argv.append(arg)

    # ── Silent, Idempotent Protocol Registration (HKCU) ─────────────────────
    register_url_protocol()

    # ── Single-Instance Enforcement ──────────────────────────────────────────
    # Prevents duplicate hardware conflicts (webcam/ViGEm) by bringing
    # the existing instance to the foreground if already running.
    is_single, _mutex = check_or_create_single_instance()
    if not is_single:
        logging.getLogger(__name__).info("DriveByGesture is already running. Existing window activated.")
        return 0

    app = QApplication(sanitized_argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(COMPANY)
    app.setWindowIcon(get_app_icon())

    # Show startup splash screen
    splash = DriveByGestureSplashScreen()
    splash.show()
    app.processEvents()

    splash.set_progress(20, "Loading Configuration & Profiles...")
    app.processEvents()

    splash.set_progress(50, "Initializing Camera & Gesture Tracking Engine...")
    app.processEvents()

    splash.set_progress(80, "Preparing Control Center Dashboard...")
    app.processEvents()

    window = MainWindow()
    apply_app_icon(window)

    splash.set_progress(90, "Starting DriveByGesture...")
    app.processEvents()

    splash.finish_and_transition(window, min_display_sec=5.0)

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
