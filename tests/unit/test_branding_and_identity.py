"""
tests.unit.test_branding_and_identity
======================================
Unit test suite for Phase 13.1 — Application Branding, Version System, Resource Manager,
Window Title Standardization, Splash Screen, and PyInstaller Metadata.
"""

import unittest
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

_app = QApplication.instance() or QApplication([])


class TestBrandingAndIdentity(unittest.TestCase):
    def test_core_version_module(self):
        from core.version import (
            APP_NAME,
            BUILD_NUMBER,
            DEVELOPER,
            VERSION,
            get_version_info,
            get_window_title,
        )

        self.assertEqual(APP_NAME, "DriveByGesture")
        self.assertEqual(VERSION, "1.0.0")
        self.assertIn("RC1", BUILD_NUMBER)
        self.assertTrue(DEVELOPER)

        self.assertEqual(get_window_title(), "DriveByGesture")
        self.assertEqual(get_window_title("Settings"), "Settings — DriveByGesture")
        self.assertEqual(get_window_title("Calibration Wizard"), "Calibration Wizard — DriveByGesture")

        info = get_version_info()
        self.assertEqual(info["app_name"], "DriveByGesture")

    def test_core_resources_manager(self):
        from core.resources import apply_app_icon, get_app_icon, get_resource_path
        from PySide6.QtWidgets import QWidget

        path = get_resource_path("resources/icons/app.ico")
        self.assertTrue(isinstance(path, Path))

        icon = get_app_icon()
        self.assertTrue(isinstance(icon, QIcon))
        self.assertFalse(icon.isNull())

        w = QWidget()
        apply_app_icon(w)
        self.assertFalse(w.windowIcon().isNull())

    def test_pyinstaller_metadata_generator(self):
        from core.pyinstaller_metadata import (
            generate_spec_file_content,
            generate_version_file_content,
            get_pyinstaller_metadata,
        )

        meta = get_pyinstaller_metadata()
        self.assertEqual(meta["product_name"], "DriveByGesture")
        self.assertEqual(meta["internal_name"], "DriveByGesture")

        ver_txt = generate_version_file_content()
        self.assertIn("DriveByGesture", ver_txt)
        self.assertIn("StringFileInfo", ver_txt)

        spec_txt = generate_spec_file_content()
        self.assertIn("app.py", spec_txt)

    def test_splash_screen_progress_and_transition(self):
        import time
        from PySide6.QtWidgets import QWidget
        from gui.splash_screen import DriveByGestureSplashScreen

        splash = DriveByGestureSplashScreen()
        splash.set_progress(50, "Loading Engine...")
        self.assertEqual(splash.progress_bar.value(), 50)
        self.assertEqual(splash.lbl_status.text(), "Loading Engine...")

        w = QWidget()
        t0 = time.time()
        splash.finish_and_transition(w, min_display_sec=0.2)
        dt = time.time() - t0
        self.assertGreaterEqual(dt, 0.2)

    def test_window_title_and_icon_standardization(self):
        from core.version import get_window_title
        from gui.help_dialog import HelpCenterDialog

        help_dialog = HelpCenterDialog()
        self.assertEqual(help_dialog.windowTitle(), get_window_title("Help Center"))
        self.assertFalse(help_dialog.windowIcon().isNull())


if __name__ == "__main__":
    unittest.main()
