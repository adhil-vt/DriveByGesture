"""
gesturedrive.gui.main_window
============================
MainWindow: Master dashboard interface assembling Top Bar, Camera Preview, Telemetry Dashboard,
Status Bar, Control Panel, and Pipeline Worker thread.
"""

from __future__ import annotations

import logging
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from gui.calibration_dialog import CalibrationDialog
from gui.camera_widget import CameraWidget
from gui.control_panel import ControlPanelWidget
from gui.settings_dialog import SettingsDialog
from gui.status_bar import StatusBarWidget
from gui.styles import DARK_THEME_QSS
from gui.telemetry_panel import TelemetryPanel
from gui.top_bar import TopBarWidget
from gui.worker import PipelineWorker

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """
    Main Application Control Center Window.
    """

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("DriveByGesture")
        self.resize(1400, 850)
        self.setMinimumSize(1280, 800)

        # Apply commercial dark theme QSS
        self.setStyleSheet(DARK_THEME_QSS)

        # Central Widget & Root Layout
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(14)

        # 1. Top Bar
        self.top_bar = TopBarWidget()
        root_layout.addWidget(self.top_bar)

        # 2. Main Dashboard Area (Left Area ≈ 70%: Camera Preview, Right Area ≈ 30%: Telemetry Panel)
        dash_layout = QHBoxLayout()
        dash_layout.setSpacing(14)

        self.camera_widget = CameraWidget()
        self.telemetry_panel = TelemetryPanel()

        dash_layout.addWidget(self.camera_widget, stretch=7)
        dash_layout.addWidget(self.telemetry_panel, stretch=3)

        root_layout.addLayout(dash_layout, stretch=1)

        # 3. Bottom Status Bar
        self.status_bar_widget = StatusBarWidget()
        root_layout.addWidget(self.status_bar_widget)

        # 4. Bottom Control Panel
        self.control_panel = ControlPanelWidget()
        root_layout.addWidget(self.control_panel)

        # Worker Thread & Active Dialog handles
        self.worker: PipelineWorker | None = None
        self.active_calib_dialog: CalibrationDialog | None = None

        # Connect Control Panel signals
        self.control_panel.start_requested.connect(self.start_pipeline)
        self.control_panel.stop_requested.connect(self.stop_pipeline)
        self.control_panel.calibrate_requested.connect(self.open_calibration_wizard)
        self.control_panel.settings_requested.connect(self.open_settings_window)
        self.control_panel.exit_requested.connect(self.close)

    def start_pipeline(self) -> None:
        """Start the background backend pipeline worker thread."""
        if self.worker is not None and self.worker.isRunning():
            return

        logger.info("Starting backend pipeline thread...")
        self.top_bar.update_status("Starting...", "#ffb300")
        self.control_panel.set_pipeline_running(True)

        self.worker = PipelineWorker()
        self.worker.frame_processed.connect(self._on_frame_processed)
        self.worker.status_changed.connect(self._on_status_changed)
        self.worker.error_occurred.connect(self._on_error_occurred)
        self.worker.finished.connect(self._on_worker_finished)

        self.worker.start()

    def stop_pipeline(self) -> None:
        """Stop the running backend pipeline worker thread safely."""
        if self.worker is not None and self.worker.isRunning():
            logger.info("Stopping backend pipeline thread...")
            self.top_bar.update_status("Stopping...", "#ffb300")
            self.worker.stop()
            self.worker.wait(3000)

        self._on_worker_finished()

    def open_calibration_wizard(self) -> None:
        """Launch graphical Calibration Wizard dialog."""
        if self.worker is None or not self.worker.isRunning():
            self.start_pipeline()
            # Brief wait for worker initialization
            QApplication.processEvents()

        if self.worker is None or self.worker.calibration_manager is None:
            QMessageBox.warning(self, "Calibration Error", "Pipeline worker is not initialized.")
            return

        logger.info("Opening Calibration Wizard dialog...")
        dialog = CalibrationDialog(self.worker.calibration_manager, self)
        self.active_calib_dialog = dialog
        result = dialog.exec()
        self.active_calib_dialog = None

        if result == CalibrationDialog.DialogCode.Accepted:
            self.status_bar_widget.set_component_status("Calibration", "Loaded", "good")

    def open_settings_window(self) -> None:
        """Launch graphical Settings & Configuration dialog."""
        if self.worker is None or not self.worker.isRunning():
            self.start_pipeline()
            QApplication.processEvents()

        if self.worker is None or self.worker.calibration_manager is None:
            QMessageBox.warning(self, "Settings Error", "Pipeline worker is not initialized.")
            return

        logger.info("Opening Settings dialog...")
        dialog = SettingsDialog(self.worker.calibration_manager, self)
        dialog.config_applied.connect(self._on_live_config_applied)
        dialog.open_wizard_requested.connect(self.open_calibration_wizard)
        dialog.exec()

    def _on_live_config_applied(self, camera_config, steering_config) -> None:
        """Apply live configuration changes defensively to UI and worker pipeline thread."""
        try:
            if camera_config and hasattr(camera_config, "mirror_preview"):
                self.camera_widget.mirror_preview = getattr(camera_config, "mirror_preview", True)

            if self.worker:
                self.worker.apply_live_config(camera_config, steering_config)
                logger.info("Live configuration updated on MainWindow.")
        except Exception as exc:
            logger.warning("MainWindow live configuration update skipped safely: %s", exc)

    def _on_frame_processed(self, frame: np.ndarray, fps: float, telemetry: dict) -> None:
        """Handle incoming processed video frame and live telemetry metrics."""
        self.camera_widget.update_frame(frame, overlay_info=telemetry)
        self.top_bar.update_fps(fps)
        self.top_bar.update_status("Running", "#00e676")
        self.top_bar.update_info(
            profile_name=telemetry.get("profile_name"),
            camera_name=telemetry.get("camera_name"),
        )
        self.telemetry_panel.update_telemetry_data(telemetry)

        # Route calibration frame and snapshot to active dialog if open
        if self.active_calib_dialog is not None and self.active_calib_dialog.isVisible():
            snap = telemetry.get("calibration_snapshot")
            self.active_calib_dialog.update_telemetry_frame(frame, snap)

    def _on_status_changed(self, component: str, status_str: str, state: str) -> None:
        """Update status bar indicators from worker thread."""
        self.status_bar_widget.set_component_status(component, status_str, state)

    def _on_error_occurred(self, title: str, message: str) -> None:
        """Handle backend runtime error dialog without crashing the GUI."""
        logger.error("GUI Error Event: %s — %s", title, message)
        self.camera_widget.show_error_banner(title)
        QMessageBox.warning(self, title, message)

    def _on_worker_finished(self) -> None:
        """Called when worker thread stops or terminates."""
        self.control_panel.set_pipeline_running(False)
        self.top_bar.update_status("Stopped", "#8f96a3")
        self.top_bar.update_fps(0.0)
        self.camera_widget.show_offline_banner("Camera Offline")

    def closeEvent(self, event: QCloseEvent) -> None:
        """Ensure clean shutdown of pipeline worker and resources on window close."""
        logger.info("Window close requested. Performing graceful shutdown...")
        if self.worker is not None and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(2000)
        event.accept()
