"""
gesturedrive.gui.settings_dialog
================================
SettingsDialog: 900x650 commercial settings window with left category navigation and stacked pages.
"""

from __future__ import annotations

import logging
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
)

from calibration.calibration_manager import CalibrationManager
from config.schema import CameraConfig, GestureConfig
from gui.settings_pages import (
    AboutPage,
    CalibrationPage,
    CameraPage,
    ControllerPage,
    DesktopPage,
    GeneralPage,
    ProfilePage,
    SteeringPage,
)
from gui.styles import DARK_THEME_QSS

from core.resources import apply_app_icon
from core.version import get_window_title

logger = logging.getLogger(__name__)


class SettingsDialog(QDialog):
    """
    Application Settings & Configuration Modal Dialog.
    """

    config_applied = Signal(object, object)  # (CameraConfig, GestureConfig)
    open_wizard_requested = Signal()
    reconnect_controller_requested = Signal()

    def __init__(self, calibration_manager: CalibrationManager, parent=None) -> None:
        super().__init__(parent)
        self.manager = calibration_manager

        self.setWindowTitle(get_window_title("Settings"))
        apply_app_icon(self)
        self.resize(900, 650)
        self.setMinimumSize(850, 600)
        self.setModal(True)
        self.setStyleSheet(DARK_THEME_QSS)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(12)

        # Main Split Area (Left: Navigation List, Right: Stacked Pages)
        main_split = QHBoxLayout()
        main_split.setSpacing(14)

        # Left Sidebar Navigation
        self.nav_list = QListWidget()
        self.nav_list.setMinimumWidth(200)
        self.nav_list.setMaximumWidth(240)
        self.nav_list.setStyleSheet(
            "QListWidget { background-color: #14161f; border: 1px solid #282c3c; border-radius: 10px; padding: 6px; }"
            "QListWidget::item { padding: 12px 14px; border-radius: 6px; font-weight: 600; font-size: 13px; color: #8f96a3; }"
            "QListWidget::item:selected { background-color: #1a1d28; color: #00e5ff; border: 1px solid #00e5ff; }"
            "QListWidget::item:hover:!selected { background-color: #1c202d; color: #ffffff; }"
        )

        nav_items = [
            ("⚙   General", 0),
            ("🖥️   Desktop Controls", 1),
            ("📷   Camera", 2),
            ("☸   Steering", 3),
            ("🎮   Controller", 4),
            ("🎯   Calibration", 5),
            ("👤   Profiles", 6),
            ("ℹ️   About", 7),
        ]

        for title, index in nav_items:
            item = QListWidgetItem(title)
            item.setData(Qt.ItemDataRole.UserRole, index)
            self.nav_list.addItem(item)

        main_split.addWidget(self.nav_list)

        # Right Stacked Pages Container
        self.pages_stack = QStackedWidget()

        self.page_general = GeneralPage()
        self.page_desktop = DesktopPage()
        self.page_camera = CameraPage()
        self.page_steering = SteeringPage()
        self.page_controller = ControllerPage()
        self.page_calibration = CalibrationPage(self.manager)
        self.page_profiles = ProfilePage()
        self.page_about = AboutPage()

        self.pages_stack.addWidget(self.page_general)
        self.pages_stack.addWidget(self.page_desktop)
        self.pages_stack.addWidget(self.page_camera)
        self.pages_stack.addWidget(self.page_steering)
        self.pages_stack.addWidget(self.page_controller)
        self.pages_stack.addWidget(self.page_calibration)
        self.pages_stack.addWidget(self.page_profiles)
        self.pages_stack.addWidget(self.page_about)

        main_split.addWidget(self.pages_stack, stretch=1)
        root_layout.addLayout(main_split, stretch=1)

        # Bottom Action Bar
        btn_box = QHBoxLayout()
        btn_box.setSpacing(12)

        self.btn_reset_defaults = QPushButton("🔄   Reset to Defaults")
        self.btn_reset_defaults.clicked.connect(self._on_reset_defaults)

        self.btn_apply = QPushButton("Apply")
        self.btn_apply.setObjectName("btnStart")
        self.btn_apply.clicked.connect(self._on_apply)

        self.btn_ok = QPushButton("OK")
        self.btn_ok.setObjectName("btnStart")
        self.btn_ok.clicked.connect(self._on_ok)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setObjectName("btnExit")
        self.btn_cancel.clicked.connect(self.reject)

        btn_box.addWidget(self.btn_reset_defaults)
        btn_box.addStretch()
        btn_box.addWidget(self.btn_apply)
        btn_box.addWidget(self.btn_ok)
        btn_box.addWidget(self.btn_cancel)

        root_layout.addLayout(btn_box)

        # Connections
        self.nav_list.currentRowChanged.connect(self.pages_stack.setCurrentIndex)
        self.nav_list.setCurrentRow(0)

        self.page_calibration.open_wizard_requested.connect(self._on_open_wizard)
        self.page_calibration.reset_calibration_requested.connect(self._on_reset_calibration)
        self.page_controller.reconnect_requested.connect(self.reconnect_controller_requested.emit)

    def _on_apply(self) -> None:
        """Apply current settings to running application live and save to disk."""
        try:
            cam_cfg = self.page_camera.get_config()
            steer_cfg = self.page_steering.get_config()
            desk_cfg = self.page_desktop.get_config()
            ctrl_cfg = self.page_controller.get_config() if hasattr(self.page_controller, "get_config") else None
            gen_cfg = self.page_general.get_config() if hasattr(self.page_general, "get_config") else None

            # Apply UI preview display preferences directly to camera widget if parent is MainWindow
            if self.parent() and hasattr(self.parent(), "camera_widget"):
                cw = getattr(self.parent(), "camera_widget")
                cw.mirror_preview = self.page_camera.is_mirror_preview_enabled()
                cw.overlay_enabled = self.page_camera.is_show_overlay_enabled()

            if self.parent() and hasattr(self.parent(), "mode_manager"):
                mm = getattr(self.parent(), "mode_manager")
                target_mode = desk_cfg.get("mode", "driving")
                mm.set_mode(target_mode)

            if self.parent() and hasattr(self.parent(), "worker") and self.parent().worker:
                worker = self.parent().worker
                if hasattr(worker, "desktop_controller") and worker.desktop_controller:
                    worker.desktop_controller.apply_config(desk_cfg)
                if hasattr(worker, "apply_live_config"):
                    worker.apply_live_config(cam_cfg, steer_cfg)
                if ctrl_cfg and hasattr(worker, "apply_controller_config"):
                    worker.apply_controller_config(ctrl_cfg)

            # Persist settings to Active Profile and save to disk
            if self.parent() and hasattr(self.parent(), "profile_manager"):
                pm = getattr(self.parent(), "profile_manager")
                active_p = getattr(pm, "active_profile", None) or getattr(pm, "active", None)
                if active_p:
                    if hasattr(active_p, "apply_desktop_config"):
                        active_p.apply_desktop_config(desk_cfg)
                    elif hasattr(active_p, "desktop") and isinstance(active_p.desktop, dict):
                        active_p.desktop.update(desk_cfg)

                    if hasattr(active_p, "apply_camera_config"):
                        active_p.apply_camera_config(cam_cfg)
                    elif hasattr(cam_cfg, "to_dict") and hasattr(active_p, "camera") and isinstance(active_p.camera, dict):
                        active_p.camera.update(cam_cfg.to_dict())

                    if hasattr(active_p, "apply_gesture_config"):
                        active_p.apply_gesture_config(steer_cfg)
                    elif hasattr(steer_cfg, "to_dict") and hasattr(active_p, "steering") and isinstance(active_p.steering, dict):
                        active_p.steering.update(steer_cfg.to_dict())

                    if ctrl_cfg:
                        if hasattr(active_p, "apply_controller_config"):
                            active_p.apply_controller_config(ctrl_cfg)
                        elif hasattr(ctrl_cfg, "to_dict") and hasattr(active_p, "controller") and isinstance(active_p.controller, dict):
                            active_p.controller.update(ctrl_cfg.to_dict())

                    if gen_cfg:
                        if hasattr(active_p, "apply_general_config"):
                            active_p.apply_general_config(gen_cfg)
                        elif hasattr(gen_cfg, "to_dict") and hasattr(active_p, "general") and isinstance(active_p.general, dict):
                            active_p.general.update(gen_cfg.to_dict())

                    pm.save_active()
                    logger.info("Active profile '%s' updated and saved to disk.", active_p.name)

            self.config_applied.emit(cam_cfg, steer_cfg)
            logger.info("Settings applied live and saved to disk.")
        except Exception as exc:
            logger.error("Failed to apply settings: %s", exc)
            QMessageBox.critical(self, "Settings Error", f"Failed to apply settings: {exc}")

    def _on_ok(self) -> None:
        """Apply settings and close dialog."""
        self._on_apply()
        self.accept()

    def update_telemetry(self, telemetry: dict) -> None:
        """Forward live telemetry to Desktop Controls page for real-time monitoring and table highlighting."""
        if hasattr(self, "page_desktop") and hasattr(self.page_desktop, "update_telemetry"):
            self.page_desktop.update_telemetry(telemetry)

    def _on_reset_defaults(self) -> None:
        """Reset all page inputs to default configuration across every settings section."""
        reply = QMessageBox.question(
            self,
            "Reset All Settings to Defaults",
            "Are you sure you want to reset ALL settings (Camera, Steering, Controller, Desktop Controls, General) to factory defaults?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        if hasattr(self.page_camera, "reset_to_defaults"):
            self.page_camera.reset_to_defaults()
        if hasattr(self.page_steering, "reset_to_defaults"):
            self.page_steering.reset_to_defaults()
        if hasattr(self.page_controller, "reset_to_defaults"):
            self.page_controller.reset_to_defaults()
        if hasattr(self.page_desktop, "reset_desktop_controls"):
            self.page_desktop.reset_desktop_controls()
        if hasattr(self.page_general, "reset_to_defaults"):
            self.page_general.reset_to_defaults()

        self._on_apply()

        QMessageBox.information(
            self,
            "Reset Defaults",
            "All settings have been reset to factory defaults and applied to the active profile.",
        )

    def _on_open_wizard(self) -> None:
        self.open_wizard_requested.emit()
        self.accept()

    def _on_reset_calibration(self) -> None:
        reply = QMessageBox.question(
            self,
            "Reset Calibration",
            "Are you sure you want to reset steering calibration to default configuration?\nThis will delete profiles/default_calibration.json.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.manager.reset_calibration()
            self.page_calibration.update_status()
            QMessageBox.information(self, "Reset Complete", "Calibration reset to default configuration.")
