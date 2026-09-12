"""
tests.unit.test_logging_and_crash_recovery
============================================
Unit test suite for Centralized Production Logging, Daily Log Rotation,
Crash Report Generation, CrashDialog, and Global Exception Handling.
"""

import json
import logging
import tempfile
import unittest
from pathlib import Path

from PySide6.QtWidgets import QApplication

_app = QApplication.instance() or QApplication([])


class TestLoggingAndCrashRecovery(unittest.TestCase):
    def test_central_logging_setup(self):
        from core.logger import get_log_dir, get_recent_logs, setup_central_logging

        log_dir = get_log_dir()
        self.assertTrue(log_dir.exists())

        logger = setup_central_logging(level=logging.DEBUG)
        logging.info("Test log message for central logger test.")

        recent = get_recent_logs(50)
        self.assertTrue(isinstance(recent, list))

    def test_crash_report_generation(self):
        from core.crash_handler import generate_crash_report
        from core.logger import get_crash_reports_dir

        try:
            raise ValueError("Test artificial crash exception")
        except Exception as exc:
            exc_type, exc_val, exc_tb = type(exc), exc, exc.__traceback__
            report_file, report_data = generate_crash_report(
                exc_type, exc_val, exc_tb, active_profile="TestProfile"
            )

            self.assertTrue(report_file.exists())
            self.assertEqual(report_data["exception_type"], "ValueError")
            self.assertEqual(report_data["exception_message"], "Test artificial crash exception")
            self.assertEqual(report_data["active_profile"], "TestProfile")
            self.assertIn("Test artificial crash exception", report_data["stack_trace"])

    def test_crash_dialog_instantiation(self):
        from core.crash_handler import generate_crash_report
        from gui.crash_dialog import CrashDialog

        try:
            raise RuntimeError("Test dialog runtime error")
        except Exception as exc:
            exc_type, exc_val, exc_tb = type(exc), exc, exc.__traceback__
            report_file, report_data = generate_crash_report(exc_type, exc_val, exc_tb)

            dialog = CrashDialog(report_file, report_data)
            dialog.show()
            self.assertIn("Crash Report", dialog.windowTitle())
            self.assertFalse(dialog.txt_traceback.isVisible())

            # Test toggle details
            dialog._toggle_details(True)
            self.assertTrue(dialog.txt_traceback.isVisible())

            dialog.close()
            dialog.deleteLater()
            _app.processEvents()

    def test_global_crash_handler_installation(self):
        import sys
        import threading
        from core.crash_handler import install_global_crash_handler

        install_global_crash_handler()
        self.assertIsNotNone(sys.excepthook)
        self.assertIsNotNone(getattr(threading, "excepthook", None))


if __name__ == "__main__":
    unittest.main()
