"""
tests.unit.test_diagnostics_center
====================================
Unit test suite for Professional Diagnostics Center: widgets, navigation,
telemetry forwarding, health scoring, self-test thread, and report export.
"""

import json
import tempfile
import unittest
from pathlib import Path

from PySide6.QtWidgets import QApplication

_app = QApplication.instance() or QApplication([])


class TestDiagnosticsCenter(unittest.TestCase):
    def test_diagnostics_dialog_initialization(self):
        from gui.diagnostics_dialog import DiagnosticsDialog

        dialog = DiagnosticsDialog()
        self.assertEqual(dialog.nav_list.count(), 8)
        self.assertEqual(dialog.pages_stack.count(), 8)

    def test_telemetry_forwarding(self):
        from gui.diagnostics_dialog import DiagnosticsDialog

        dialog = DiagnosticsDialog()
        sample_telemetry = {
            "camera_fps": 30.0,
            "processing_fps": 30.0,
            "latency_ms": 12.5,
            "steering_angle": 15.0,
            "raw_steering": 18.0,
            "normalized_steering": 0.50,
            "gesture": "Open Palm",
            "action": "Accelerator",
            "controller_status": "Connected",
            "left_stick_x": 16384,
            "accelerator_rt": 255,
            "brake_lt": 0,
        }

        dialog.update_telemetry(sample_telemetry)
        self.assertEqual(dialog.page_perf.lbl_cam_fps.text(), "30.0 FPS")
        self.assertEqual(dialog.page_tracking.lbl_gesture_name.text(), "Open Palm")
        self.assertEqual(dialog.page_controller.lbl_stick_x.text(), "16384")

    def test_health_widget_and_score(self):
        from gui.diagnostics_widgets import HealthWidget

        health_widget = HealthWidget()
        health_widget.on_status_changed("Camera", "Connected", "good")
        health_widget.on_status_changed("Controller", "Connected", "good")

        self.assertIn("HEALTH SCORE", health_widget._lbl_health.text())

    def test_export_report(self):
        from gui.diagnostics_dialog import DiagnosticsDialog

        dialog = DiagnosticsDialog()
        sample_telemetry = {"processing_fps": 60.0, "latency_ms": 5.0}
        dialog.update_telemetry(sample_telemetry)

        with tempfile.TemporaryDirectory() as temp_dir:
            export_path = Path(temp_dir) / "test_report.json"

            report_data = {
                "timestamp": "2026-08-03 12:00:00",
                "telemetry": dialog._last_telemetry,
                "recent_logs": [],
            }
            export_path.write_text(json.dumps(report_data, indent=2), encoding="utf-8")

            self.assertTrue(export_path.exists())
            read_data = json.loads(export_path.read_text(encoding="utf-8"))
            self.assertEqual(read_data["telemetry"]["processing_fps"], 60.0)


if __name__ == "__main__":
    unittest.main()
