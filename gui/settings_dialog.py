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
    GeneralPage,
    ProfilePage,
    SteeringPage,
)
from gui.styles import DARK_THEME_QSS

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

        self.setWindowTitle("DriveByGesture — Settings & Configuration")
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
            ("📷   Camera", 1),
            ("☸   Steering", 2),
            ("🎮   Controller", 3),
            ("🎯   Calibration", 4),
            ("👤   Profiles", 5),
            ("ℹ️   About", 6),
        ]

        for title, index in nav_items:
            item = QListWidgetItem(title)
            item.setData(Qt.ItemDataRole.UserRole, index)
            self.nav_list.addItem(item)

        main_split.addWidget(self.nav_list)

        # Right Stacked Pages Container
        self.pages_stack = QStackedWidget()

        self.page_general = GeneralPage()
        self.page_camera = CameraPage()
        self.page_steering = SteeringPage()
        self.page_controller = ControllerPage()
        self.page_calibration = CalibrationPage(self.manager)
        self.page_profiles = ProfilePage()
        self.page_about = AboutPage()

        self.pages_stack.addWidget(self.page_general)
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
        """Apply current settings to running application live."""
        try:
            cam_cfg = self.page_camera.get_config()
            steer_cfg = self.page_steering.get_config()

            # Apply UI preview display preferences directly to camera widget if parent is MainWindow
            if self.parent() and hasattr(self.parent(), "camera_widget"):
                cw = getattr(self.parent(), "camera_widget")
                cw.mirror_preview = self.page_camera.is_mirror_preview_enabled()
                cw.overlay_enabled = self.page_camera.is_show_overlay_enabled()

            self.config_applied.emit(cam_cfg, steer_cfg)
            logger.info("Settings applied live.")
        except Exception as exc:
            logger.error("Failed to apply settings: %s", exc)
            QMessageBox.critical(self, "Settings Error", f"Failed to apply settings: {exc}")

    def _on_ok(self) -> None:
        """Apply settings and close dialog."""
        self._on_apply()
        self.accept()

    def _on_reset_defaults(self) -> None:
        """Reset page inputs to default configuration."""
        self.page_steering.dsp_sensitivity.setValue(1.0)
        self.page_steering.dsp_deadzone.setValue(0.05)
        self.page_steering.sb_max_angle.setValue(30)
        self.page_steering.dsp_smoothing.setValue(0.3)
        self.page_steering.cb_invert.setChecked(False)
        QMessageBox.information(self, "Reset Defaults", "Steering and Camera settings reset to defaults. Click Apply to save.")

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
