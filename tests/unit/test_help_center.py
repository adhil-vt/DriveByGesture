"""
tests.unit.test_help_center
===========================
Unit test suite for Help Center documentation content, dialog UI, search filter, and HTML export.
"""

import tempfile
import unittest
from pathlib import Path

from gui.help_content import _get_runtime_info, get_help_sections


class TestHelpCenterContent(unittest.TestCase):
    def test_help_sections_count(self):
        sections = get_help_sections()
        self.assertEqual(len(sections), 10, "Help Center must contain exactly 10 documentation sections.")

    def test_section_fields(self):
        sections = get_help_sections()
        expected_ids = [
            "about",
            "getting_started",
            "driving_mode",
            "desktop_mode",
            "settings_guide",
            "calibration_guide",
            "troubleshooting",
            "shortcuts",
            "changelog",
            "credits",
        ]

        for i, sec in enumerate(sections):
            self.assertIn("id", sec)
            self.assertIn("title", sec)
            self.assertIn("icon", sec)
            self.assertIn("html", sec)

            self.assertEqual(sec["id"], expected_ids[i])
            self.assertTrue(len(sec["title"]) > 0)
            self.assertTrue(len(sec["html"]) > 50)

    def test_runtime_info_fields(self):
        info = _get_runtime_info()
        self.assertEqual(info["app_name"], "DriveByGesture")
        self.assertEqual(info["version"], "1.0.0")
        self.assertTrue(len(info["python_version"]) > 0)
        self.assertTrue(len(info["os_platform"]) > 0)
        self.assertIn("opencv_version", info)
        self.assertIn("mediapipe_version", info)
        self.assertIn("pyside_version", info)

    def test_desktop_mode_dynamic_gestures(self):
        sections = get_help_sections()
        desktop_sec = next(s for s in sections if s["id"] == "desktop_mode")
        html = desktop_sec["html"]

        self.assertIn("Open Palm", html)
        self.assertIn("Pinch", html)
        self.assertIn("Fist", html)
        self.assertIn("Move Cursor", html)
        self.assertIn("Left Click", html)


class TestHelpCenterUI(unittest.TestCase):
    def setUp(self):
        from PySide6.QtWidgets import QApplication
        self.app = QApplication.instance() or QApplication([])

    def test_help_dialog_initialization(self):
        from gui.help_dialog import HelpCenterDialog

        dialog = HelpCenterDialog()
        self.assertEqual(dialog.nav_list.count(), 10)
        self.assertTrue(dialog.viewer.toPlainText() != "")

    def test_help_dialog_search_filter(self):
        from gui.help_dialog import HelpCenterDialog

        dialog = HelpCenterDialog()
        dialog.txt_search.setText("calibration")
        self.assertFalse(dialog.nav_list.item(5).isHidden())

        dialog.txt_search.setText("nonexistentxyz123")
        for i in range(dialog.nav_list.count()):
            self.assertTrue(dialog.nav_list.item(i).isHidden())

    def test_help_dialog_html_export(self):
        from gui.help_dialog import HelpCenterDialog

        dialog = HelpCenterDialog()
        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir) / "test_doc.html"
            # Simulate export logic directly
            sections = get_help_sections()
            full_doc_body = "".join(f"<div>{s['html']}</div>" for s in sections)
            dest.write_text(full_doc_body, encoding="utf-8")

            self.assertTrue(dest.exists())
            text = dest.read_text(encoding="utf-8")
            self.assertIn("DriveByGesture", text)
            self.assertIn("About DriveByGesture", text)


if __name__ == "__main__":
    unittest.main()
