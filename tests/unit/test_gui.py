import sys
import unittest
import numpy as np
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from gui.camera_widget import CameraWidget
from gui.control_panel import ControlPanelWidget
from gui.controller_widget import ControllerWidget
from gui.gesture_widget import GestureWidget
from gui.main_window import MainWindow
from gui.stats_widget import PipelineStatsWidget
from gui.status_bar import StatusBarWidget
from gui.steering_wheel import SteeringWheelWidget
from gui.steering_widget import LiveSteeringBar, SteeringWidget
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
        self.assertEqual(window.minimumWidth(), 1280)
        self.assertEqual(window.minimumHeight(), 800)

    def test_top_bar_widget(self):
        top_bar = TopBarWidget()
        self.assertEqual(top_bar.lbl_title.text(), "DriveByGesture")

        top_bar.update_fps(59.8)
        self.assertIn("59.8", top_bar.lbl_fps.text())

        top_bar.update_status("Running", "#00e676")
        self.assertIn("Running", top_bar.lbl_status.text())

        top_bar.profile_selector.set_profiles(["CustomProfile"])
        top_bar.update_info("CustomProfile", "Webcam 0")
        self.assertEqual(top_bar.profile_selector.current_profile_name(), "CustomProfile")
        self.assertIn("Webcam 0", top_bar.lbl_camera.text())

    def test_camera_widget_banners_and_overlay(self):
        cam_widget = CameraWidget()
        cam_widget.show_offline_banner("Camera Offline")
        self.assertIn("Camera Offline", cam_widget.lbl_image.text())

        cam_widget.show_error_banner("Camera Error")
        self.assertIn("Camera Error", cam_widget.lbl_image.text())

        # Test frame rendering with HUD overlay info
        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        overlay = {
            "fps": 60.0,
            "gesture": "Fist",
            "gesture_confidence": 0.98,
            "steering_angle": -15.4,
            "tracking_confidence": 0.95,
        }
        cam_widget.update_frame(dummy_frame, overlay_info=overlay)
        self.assertIsNotNone(cam_widget.lbl_image.pixmap())

    def test_steering_wheel_widget(self):
        wheel = SteeringWheelWidget()
        wheel.set_angle(-18.5)
        self.assertEqual(wheel.steering_angle, -18.5)
        wheel.set_angle(24.2)
        self.assertEqual(wheel.steering_angle, 24.2)

    def test_steering_widget_and_live_bar(self):
        sw = SteeringWidget()
        sw.update_metrics(angle_deg=-18.4, direction="LEFT", norm_val=-0.62, raw_angle=-18.4)
        self.assertEqual(sw.val_angle.text(), "-18.4°")
        self.assertEqual(sw.val_direction.text(), "LEFT")
        self.assertEqual(sw.val_norm.text(), "-0.62")

        bar = LiveSteeringBar()
        bar.set_value(-0.75)
        self.assertEqual(bar.normalized_val, -0.75)

    def test_gesture_widget(self):
        gw = GestureWidget()
        gw.update_gesture(gesture_name="Fist", confidence=0.98, action_name="Handbrake")
        self.assertEqual(gw.val_gesture.text(), "Fist")
        self.assertEqual(gw.pb_confidence.value(), 98)
        self.assertEqual(gw.val_action.text(), "Handbrake")

    def test_controller_widget(self):
        cw = ControllerWidget()
        cw.update_controller(status="Connected (ViGEmBus)", stick_x=-20318, rt_val=255, lt_val=0, buttons="Button A")
        self.assertEqual(cw.val_status.text(), "Connected (ViGEmBus)")
        self.assertEqual(cw.pb_stick_x.value(), -20318)
        self.assertEqual(cw.pb_rt.value(), 255)
        self.assertEqual(cw.pb_lt.value(), 0)
        self.assertEqual(cw.val_buttons.text(), "Button A")

    def test_pipeline_stats_widget(self):
        ps = PipelineStatsWidget()
        ps.update_stats(camera_fps=30.0, proc_fps=60.0, latency_ms=16.6, tracking_conf=0.96)
        self.assertEqual(ps.val_cam_fps.text(), "30.0")
        self.assertEqual(ps.val_proc_fps.text(), "60.0")
        self.assertEqual(ps.val_latency.text(), "16.6 ms")
        self.assertEqual(ps.val_trk_conf.text(), "96%")

    def test_telemetry_panel_full_data_update(self):
        panel = TelemetryPanel()
        data = {
            "steering_angle": -15.2,
            "raw_steering": -15.2,
            "normalized_steering": -0.51,
            "direction": "LEFT",
            "gesture": "Open Palm",
            "gesture_confidence": 0.94,
            "action": "Accelerator",
            "camera_fps": 30.0,
            "processing_fps": 59.8,
            "latency_ms": 16.7,
            "tracking_confidence": 0.95,
            "controller_status": "Connected (ViGEmBus)",
            "left_stick_x": -16700,
            "accelerator_rt": 255,
            "brake_lt": 0,
            "buttons_pressed": "None",
        }
        panel.update_telemetry_data(data)
        self.assertEqual(panel.steering_wheel.steering_angle, -15.2)
        self.assertEqual(panel.steering_widget.val_direction.text(), "LEFT")
        self.assertEqual(panel.gesture_widget.val_gesture.text(), "Open Palm")

    def test_status_bar_widget(self):
        bar = StatusBarWidget()
        bar.set_component_status("Camera", "Connected")
        self.assertIn("Connected", bar.ind_camera.text())

        bar.set_component_status("MediaPipe", "Running")
        self.assertIn("Running", bar.ind_mediapipe.text())

        bar.set_component_status("Controller", "Connected")
        self.assertIn("Connected", bar.ind_controller.text())

        bar.set_component_status("Calibration", "Loaded")
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

    def test_calibration_progress_widget(self):
        from gui.calibration_progress import CalibrationProgressWidget
        from calibration.calibration_session import CalibrationStep

        cp = CalibrationProgressWidget()
        cp.set_step(CalibrationStep.LEFT)
        self.assertIn("●", cp.chip_left.text())
        self.assertIn("✓", cp.chip_center.text())

    def test_calibration_review_widget(self):
        from gui.calibration_review import ReviewWidget
        from calibration.calibration_data import CalibrationData

        rw = ReviewWidget()
        data = CalibrationData(center_angle=1.2, left_limit=-25.4, right_limit=28.1)
        rw.set_calibration_data(data)
        self.assertEqual(rw.val_center.text(), "+1.2°")
        self.assertEqual(rw.val_left.text(), "-25.4°")
        self.assertEqual(rw.val_right.text(), "+28.1°")

    def test_settings_pages(self):
        from gui.settings_pages import CameraPage, SteeringPage, GeneralPage, ControllerPage, AboutPage
        from config.schema import GeneralConfig, ControllerConfig

        # GeneralPage audit
        gen = GeneralPage()
        self.assertEqual(gen.lbl_version.text(), "1.0.0")
        gen.cb_auto_save_calib.setChecked(False)
        gen.cb_auto_start_pipeline.setChecked(True)
        gen_cfg = gen.get_config()
        self.assertFalse(gen_cfg.auto_save_calibration)
        self.assertTrue(gen_cfg.auto_start_pipeline)
        gen.reset_to_defaults()
        self.assertTrue(gen.cb_auto_save_calib.isChecked())
        self.assertFalse(gen.cb_auto_start_pipeline.isChecked())

        # CameraPage audit
        cam = CameraPage()
        cfg = cam.get_config()
        self.assertEqual(cfg.device_index, 0)
        self.assertEqual(cfg.fps, 30)

        # SteeringPage audit (including steering_inversion test)
        steer = SteeringPage()
        steer.cb_invert.setChecked(True)
        s_cfg = steer.get_config()
        self.assertEqual(s_cfg.steering_sensitivity, 1.0)
        self.assertEqual(s_cfg.steering_deadzone, 0.05)
        self.assertTrue(s_cfg.steering_inversion)
        steer.reset_to_defaults()
        self.assertFalse(steer.cb_invert.isChecked())
        self.assertFalse(steer.get_config().steering_inversion)

        # ControllerPage audit
        ctrl_page = ControllerPage()
        c_cfg = ctrl_page.get_config()
        self.assertEqual(c_cfg.emulation_type, "xbox")
        ctrl_page.combo_type.setCurrentIndex(1)
        self.assertEqual(ctrl_page.get_config().emulation_type, "null")
        ctrl_page.reset_to_defaults()
        self.assertEqual(ctrl_page.get_config().emulation_type, "xbox")

        about = AboutPage()
        self.assertTrue(about.findChild(object, name="") is not None)

    def test_desktop_controls_page(self):
        from gui.settings_pages import DesktopControlsPage, get_implemented_gestures

        page = DesktopControlsPage()
        gestures = get_implemented_gestures()
        self.assertTrue(len(gestures) >= 6)
        self.assertIn("Open Palm", gestures)
        self.assertIn("Pinch", gestures)

        # Check default config export
        cfg = page.get_config()
        self.assertEqual(cfg["cursor_sensitivity"], 1.75)
        self.assertEqual(cfg["cursor_smoothing"], 0.25)
        self.assertIn("MOVE_CURSOR", cfg["bindings"].values())

        # Check table row count
        self.assertEqual(page.table_bindings.rowCount(), len(page.DESKTOP_ACTIONS))

        # Test shortcut preset click
        page.txt_shortcut.setText("")
        page.txt_shortcut.setText("ctrl+c")
        self.assertEqual(page.txt_shortcut.text(), "ctrl+c")

        # Test live telemetry update
        telem = {
            "gesture": "Pinch",
            "desktop_action": "Left Click",
            "gesture_confidence": 0.96,
            "desktop_active": True,
        }
        page.update_telemetry(telem)
        self.assertEqual(page.lbl_test_gesture.text(), "[ Pinch ]")
        self.assertEqual(page.lbl_test_action.text(), "Left Click")
        self.assertEqual(page.lbl_test_confidence.text(), "96%")
        self.assertEqual(page.lbl_test_status.text(), "Executing")

        # Test reset
        page.dsp_sensitivity.setValue(3.5)
        page.reset_desktop_controls()
        self.assertEqual(page.dsp_sensitivity.value(), 1.75)

    def test_settings_dialog_instantiation(self):
        from gui.settings_dialog import SettingsDialog
        from calibration.calibration_manager import CalibrationManager

        mgr = CalibrationManager()
        dialog = SettingsDialog(mgr)
        from core.version import get_window_title
        self.assertEqual(dialog.windowTitle(), get_window_title("Settings"))
        self.assertEqual(dialog.width(), 900)
        self.assertEqual(dialog.height(), 650)
        self.assertEqual(dialog.nav_list.count(), 8)

        # Verify _on_apply executes cleanly without CameraConfig constructor exception
        dialog._on_apply()

        dialog.close()
        dialog.deleteLater()
        _app.processEvents()

    def test_pipeline_worker_live_apply_compatibility(self):
        from gui.worker import PipelineWorker
        from calibration.calibration_manager import CalibrationManager
        from config.schema import GestureConfig, CameraConfig

        worker = PipelineWorker()

        # Mock action engine & steering pipeline
        class MockPipeline:
            max_steering_angle = 30.0
            steering_deadzone = 0.05
            steering_sensitivity = 1.0
            steering_ema_alpha = 0.15

        class MockActionEngine:
            steering_pipeline = MockPipeline()

        worker.action_engine = MockActionEngine()

        g_cfg = GestureConfig(
            max_steering_angle=45.0,
            steering_deadzone=0.10,
            steering_sensitivity=1.5,
            steering_smoothing_alpha=0.25,
        )
        c_cfg = CameraConfig(device_index=0, width=1280, height=720, fps=30.0)

        # Should execute defensively without raising any AttributeError or TypeError
        worker.apply_live_config(c_cfg, g_cfg)
        self.assertEqual(worker.action_engine.steering_pipeline.max_steering_angle, 45.0)
        self.assertEqual(worker.action_engine.steering_pipeline.steering_deadzone, 0.10)
        self.assertEqual(worker.action_engine.steering_pipeline.steering_sensitivity, 1.5)
        self.assertEqual(worker.action_engine.steering_pipeline.steering_ema_alpha, 0.25)

    def test_calibration_dialog_instantiation(self):
        from gui.calibration_dialog import CalibrationDialog
        from calibration.calibration_manager import CalibrationManager

        mgr = CalibrationManager()
        dialog = CalibrationDialog(mgr)
        dialog.show()
        _app.processEvents()
        from core.version import get_window_title
        self.assertEqual(dialog.windowTitle(), get_window_title("Calibration Wizard"))
        self.assertEqual(dialog.width(), 900)
        self.assertEqual(dialog.height(), 650)
        self.assertTrue(dialog.welcome_view.isVisible())
        dialog.close()
        dialog.deleteLater()
        _app.processEvents()


if __name__ == "__main__":
    unittest.main()
