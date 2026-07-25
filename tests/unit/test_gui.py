"""
tests.unit.test_gui
===================
Unit tests for PySide6 Desktop GUI components, widgets, styling, status indicators, and worker signals.
"""

import sys
import unittest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from gui.camera_widget import CameraWidget
from gui.control_panel import ControlPanelWidget
from gui.main_window import MainWindow
from gui.status_bar import StatusBarWidget
from gui.telemetry_panel import TelemetryPanel
from gui.top_bar import TopBarWidget
from gui.worker import PipelineWorker


# Create a single QApplication instance for headless Qt GUI testing
_app = QApplication.instance() or QApplication(sys.argv)


class TestGUIComponents(unittest.TestCase):
    """Test PySide6 GUI widgets instantiation, signals, and UI layout properties."""

    def test_main_window_properties(self):
        window = MainWindow()
        self.assertEqual(window.windowTitle(), "DriveByGesture")
        self.assertEqual(window.width(), 1400)
        self.assertEqual(window.height(), 850)
        self.assertEqual(window.minimumWidth(), 1100)
        self.assertEqual(window.minimumHeight(), 700)

    def test_top_bar_widget(self):
        top_bar = TopBarWidget()
        self.assertEqual(top_bar.lbl_title.text(), "DriveByGesture")

        top_bar.update_fps(59.8)
        self.assertIn("59.8", top_bar.lbl_fps.text())

        top_bar.update_status("Running", "#00e676")
        self.assertIn("Running", top_bar.lbl_status.text())

    def test_camera_widget_banners(self):
        cam_widget = CameraWidget()
        cam_widget.show_offline_banner("Camera Offline")
        self.assertIn("Camera Offline", cam_widget.lbl_image.text())

        cam_widget.show_error_banner("Camera Error")
        self.assertIn("Camera Error", cam_widget.lbl_image.text())

    def test_telemetry_panel(self):
        panel = TelemetryPanel()
        panel.update_telemetry(steering_angle=12.5, gesture="Fist", action="Handbrake", controller="XboxController")
        self.assertEqual(panel.val_steering.text(), "+12.5°")
        self.assertEqual(panel.val_gesture.text(), "Fist")
        self.assertEqual(panel.val_action.text(), "Handbrake")

    def test_status_bar_widget(self):
        bar = StatusBarWidget()
        bar.set_component_status("Camera", "Connected", "good")
        self.assertIn("Connected", bar.ind_camera.text())

        bar.set_component_status("MediaPipe", "Running", "good")
        self.assertIn("Running", bar.ind_mediapipe.text())

        bar.set_component_status("Controller", "Connected", "good")
        self.assertIn("Connected", bar.ind_controller.text())

        bar.set_component_status("Calibration", "Loaded", "good")
        self.assertIn("Loaded", bar.ind_calibration.text())

    def test_control_panel_signals(self):
        panel = ControlPanelWidget()
        starts = []
        stops = []
        exits = []

        panel.start_requested.connect(lambda: starts.append(True))
        panel.stop_requested.connect(lambda: stops.append(True))
        panel.exit_requested.connect(lambda: exits.append(True))

        panel.btn_start.click()
        self.assertTrue(len(starts) > 0)

        panel.set_pipeline_running(True)
        self.assertFalse(panel.btn_start.isEnabled())
        self.assertTrue(panel.btn_stop.isEnabled())

        panel.btn_stop.click()
        self.assertTrue(len(stops) > 0)

        panel.btn_exit.click()
        self.assertTrue(len(exits) > 0)

    def test_pipeline_worker_lifecycle(self):
        worker = PipelineWorker()
        self.assertFalse(worker._running)
        worker.stop()
        self.assertFalse(worker._running)


if __name__ == "__main__":
    unittest.main()
