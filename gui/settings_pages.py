"""
gesturedrive.gui.settings_pages
==============================
Modular page widgets for SettingsDialog categories:
General, Camera, Steering, Controller, Calibration, Profiles, and About.
"""

from __future__ import annotations

import os
import platform
import sys
import cv2
import numpy as np
import PySide6
import mediapipe as mp
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from core.resources import get_default_calibration_path, get_user_profile_storage_dir, get_user_profiles_dir
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from calibration.calibration_manager import CalibrationManager
from config.schema import CameraConfig, ControllerConfig, GestureConfig
from gui.steering_widget import LiveSteeringBar


class NoWheelComboBox(QComboBox):
    """QComboBox that ignores mouse wheel scroll events so parent scroll area handles scrolling."""
    def wheelEvent(self, event) -> None:
        event.ignore()


class NoWheelSlider(QSlider):
    """QSlider that ignores mouse wheel scroll events so parent scroll area handles scrolling."""
    def wheelEvent(self, event) -> None:
        event.ignore()


class NoWheelSpinBox(QSpinBox):
    """QSpinBox that ignores mouse wheel scroll events so parent scroll area handles scrolling."""
    def wheelEvent(self, event) -> None:
        event.ignore()


class NoWheelDoubleSpinBox(QDoubleSpinBox):
    """QDoubleSpinBox that ignores mouse wheel scroll events so parent scroll area handles scrolling."""
    def wheelEvent(self, event) -> None:
        event.ignore()


class GeneralPage(QWidget):
    """General application options settings page."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        lbl_title = QLabel("GENERAL SETTINGS")
        lbl_title.setObjectName("sectionTitle")
        layout.addWidget(lbl_title)

        card = QFrame()
        card.setObjectName("statusCard")
        c_layout = QFormLayout(card)
        c_layout.setContentsMargins(16, 16, 16, 16)
        c_layout.setSpacing(12)

        self.lbl_version = QLabel("1.0.0")
        self.lbl_version.setStyleSheet("color: #00e5ff; font-weight: 700;")

        self.lbl_config_path = QLabel(str(get_default_calibration_path()))
        self.lbl_config_path.setStyleSheet("color: #8f96a3;")

        self.lbl_profile = QLabel("Default")
        self.lbl_profile.setStyleSheet("color: #ffb300; font-weight: 700;")

        self.cb_auto_save_calib = QCheckBox("Automatically save calibration on wizard completion")
        self.cb_auto_save_calib.setChecked(True)

        self.cb_auto_start_pipeline = QCheckBox("Automatically start pipeline thread on application startup")
        self.cb_auto_start_pipeline.setChecked(False)

        c_layout.addRow("Application Version:", self.lbl_version)
        c_layout.addRow("Configuration File:", self.lbl_config_path)
        c_layout.addRow("Active Profile:", self.lbl_profile)
        c_layout.addRow(self.cb_auto_save_calib)
        c_layout.addRow(self.cb_auto_start_pipeline)

        layout.addWidget(card)
        layout.addStretch()

    def get_config(self):
        from config.schema import GeneralConfig
        return GeneralConfig(
            auto_save_calibration=self.cb_auto_save_calib.isChecked(),
            auto_start_pipeline=self.cb_auto_start_pipeline.isChecked(),
        )

    def set_config(self, active_profile_or_cfg=None) -> None:
        if active_profile_or_cfg is None:
            return
        gen_cfg = {}
        if hasattr(active_profile_or_cfg, "name"):
            self.lbl_profile.setText(active_profile_or_cfg.name)
            self.lbl_config_path.setText(str(get_user_profile_storage_dir() / f"{active_profile_or_cfg.name}.json"))
            gen_cfg = getattr(active_profile_or_cfg, "general", {})
        elif hasattr(active_profile_or_cfg, "to_dict"):
            gen_cfg = active_profile_or_cfg.to_dict()
        elif isinstance(active_profile_or_cfg, dict):
            gen_cfg = active_profile_or_cfg

        if isinstance(gen_cfg, dict):
            self.cb_auto_save_calib.setChecked(bool(gen_cfg.get("auto_save_calibration", True)))
            self.cb_auto_start_pipeline.setChecked(bool(gen_cfg.get("auto_start_pipeline", False)))

    def reset_to_defaults(self) -> None:
        self.cb_auto_save_calib.setChecked(True)
        self.cb_auto_start_pipeline.setChecked(False)


class CameraPage(QWidget):
    """Camera device, resolution, FPS, and preview settings page."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        lbl_title = QLabel("CAMERA & PREVIEW CONFIGURATION")
        lbl_title.setObjectName("sectionTitle")
        layout.addWidget(lbl_title)

        card = QFrame()
        card.setObjectName("statusCard")
        c_layout = QFormLayout(card)
        c_layout.setContentsMargins(16, 16, 16, 16)
        c_layout.setSpacing(12)

        self.combo_device = NoWheelComboBox()
        self.combo_device.addItems(["0: Integrated Webcam", "1: External Camera", "2: Secondary Camera"])

        self.combo_resolution = NoWheelComboBox()
        self.combo_resolution.addItems(["640 x 480 (Recommended)", "1280 x 720 (HD)", "1920 x 1080 (FHD)"])

        self.sb_fps = NoWheelSpinBox()
        self.sb_fps.setRange(15, 60)
        self.sb_fps.setValue(30)
        self.sb_fps.setSuffix(" FPS")

        self.cb_mirror = QCheckBox("Mirror camera preview (Horizontal Flip)")
        self.cb_mirror.setChecked(True)

        self.cb_overlay = QCheckBox("Show HUD Telemetry Overlay on camera preview")
        self.cb_overlay.setChecked(True)

        c_layout.addRow("Camera Device:", self.combo_device)
        c_layout.addRow("Capture Resolution:", self.combo_resolution)
        c_layout.addRow("Target Frame Rate:", self.sb_fps)
        c_layout.addRow(self.cb_mirror)
        c_layout.addRow(self.cb_overlay)

        layout.addWidget(card)
        layout.addStretch()

    def get_config(self) -> CameraConfig:
        dev_idx = self.combo_device.currentIndex()
        res_txt = self.combo_resolution.currentText()
        if "1280" in res_txt:
            w, h = 1280, 720
        elif "1920" in res_txt:
            w, h = 1920, 1080
        else:
            w, h = 640, 480

        return CameraConfig(
            device_index=dev_idx,
            width=w,
            height=h,
            fps=self.sb_fps.value(),
            mirror_preview=self.cb_mirror.isChecked(),
            overlay_enabled=self.cb_overlay.isChecked(),
        )

    def is_mirror_preview_enabled(self) -> bool:
        return self.cb_mirror.isChecked()

    def is_show_overlay_enabled(self) -> bool:
        return self.cb_overlay.isChecked()

    def set_config(self, cfg: dict | CameraConfig) -> None:
        """Populate camera controls from dictionary or CameraConfig."""
        if not cfg:
            return
        if hasattr(cfg, "to_dict"):
            cfg = cfg.to_dict()

        dev_idx = cfg.get("device_index", 0)
        self.combo_device.setCurrentIndex(max(0, min(self.combo_device.count() - 1, int(dev_idx))))

        w = cfg.get("width", 640)
        if w >= 1920:
            self.combo_resolution.setCurrentIndex(2)
        elif w >= 1280:
            self.combo_resolution.setCurrentIndex(1)
        else:
            self.combo_resolution.setCurrentIndex(0)

        self.sb_fps.setValue(int(cfg.get("fps", 30)))
        self.cb_mirror.setChecked(bool(cfg.get("mirror_preview", True)))
        self.cb_overlay.setChecked(bool(cfg.get("overlay_enabled", True)))

    def reset_to_defaults(self) -> None:
        """Reset camera controls to factory defaults."""
        self.combo_device.setCurrentIndex(0)
        self.combo_resolution.setCurrentIndex(0)
        self.sb_fps.setValue(30)
        self.cb_mirror.setChecked(True)
        self.cb_overlay.setChecked(True)


class SteeringPage(QWidget):
    """Steering sensitivity, deadzone, curve, and live test page."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        lbl_title = QLabel("STEERING RESPONSE & PIPELINE TUNING")
        lbl_title.setObjectName("sectionTitle")
        layout.addWidget(lbl_title)

        card = QFrame()
        card.setObjectName("statusCard")
        c_layout = QFormLayout(card)
        c_layout.setContentsMargins(16, 16, 16, 16)
        c_layout.setSpacing(12)

        # 1. Sensitivity
        self.dsp_sensitivity = NoWheelDoubleSpinBox()
        self.dsp_sensitivity.setRange(0.5, 3.0)
        self.dsp_sensitivity.setSingleStep(0.1)
        self.dsp_sensitivity.setValue(1.0)

        # 2. Deadzone
        self.dsp_deadzone = NoWheelDoubleSpinBox()
        self.dsp_deadzone.setRange(0.0, 0.3)
        self.dsp_deadzone.setSingleStep(0.01)
        self.dsp_deadzone.setValue(0.05)

        # 3. Max Steering Angle
        self.sb_max_angle = NoWheelSpinBox()
        self.sb_max_angle.setRange(15, 90)
        self.sb_max_angle.setValue(30)
        self.sb_max_angle.setSuffix("°")

        # 4. Smoothing Alpha
        self.dsp_smoothing = NoWheelDoubleSpinBox()
        self.dsp_smoothing.setRange(0.05, 1.0)
        self.dsp_smoothing.setSingleStep(0.05)
        self.dsp_smoothing.setValue(0.3)

        # 5. Invert Steering
        self.cb_invert = QCheckBox("Invert Steering Direction")
        self.cb_invert.setChecked(False)

        c_layout.addRow("Steering Sensitivity:", self.dsp_sensitivity)
        c_layout.addRow("Center Deadzone:", self.dsp_deadzone)
        c_layout.addRow("Maximum Lock Angle:", self.sb_max_angle)
        c_layout.addRow("EMA Smoothing Alpha:", self.dsp_smoothing)
        c_layout.addRow(self.cb_invert)

        layout.addWidget(card)

        # Live Test Preview Gauge
        test_box = QFrame()
        test_box.setObjectName("statusCard")
        t_layout = QVBoxLayout(test_box)
        t_layout.setContentsMargins(14, 12, 14, 12)

        lbl_t_title = QLabel("LIVE RESPONSE PREVIEW:")
        lbl_t_title.setStyleSheet("color: #8f96a3; font-size: 11px; font-weight: 600;")
        t_layout.addWidget(lbl_t_title)

        self.test_bar = LiveSteeringBar()
        t_layout.addWidget(self.test_bar)
        layout.addWidget(test_box)

        layout.addStretch()

    def get_config(self) -> GestureConfig:
        base = GestureConfig()
        return GestureConfig(
            max_steering_angle=float(self.sb_max_angle.value()),
            steering_deadzone=float(self.dsp_deadzone.value()),
            steering_sensitivity=float(self.dsp_sensitivity.value()),
            steering_smoothing_alpha=float(self.dsp_smoothing.value()),
            steering_curve_exponent=base.steering_curve_exponent,
            steering_auto_center_rate=base.steering_auto_center_rate,
            steering_preferred_hand=base.steering_preferred_hand,
            steering_inversion=self.cb_invert.isChecked(),
            throttle_deadzone=base.throttle_deadzone,
            brake_z_threshold=base.brake_z_threshold,
            handbrake_hold_frames=base.handbrake_hold_frames,
            horn_hold_frames=base.horn_hold_frames,
            activation_frames=base.activation_frames,
            cooldown_seconds=base.cooldown_seconds,
            confidence_threshold=base.confidence_threshold,
            stability_timeout=base.stability_timeout,
            pinch_max_normalized_distance=base.pinch_max_normalized_distance,
            pinch_min_confidence=base.pinch_min_confidence,
            priority_open_palm=base.priority_open_palm,
            priority_point=base.priority_point,
            priority_peace=base.priority_peace,
            priority_fist=base.priority_fist,
            priority_thumbs_up=base.priority_thumbs_up,
            priority_pinch=base.priority_pinch,
        )

    def set_config(self, cfg: dict | GestureConfig) -> None:
        """Populate steering controls from dictionary or GestureConfig."""
        if not cfg:
            return
        if hasattr(cfg, "to_dict"):
            cfg = cfg.to_dict()

        self.sb_max_angle.setValue(int(cfg.get("max_steering_angle", 30)))
        self.dsp_deadzone.setValue(float(cfg.get("steering_deadzone", 0.05)))
        self.dsp_sensitivity.setValue(float(cfg.get("steering_sensitivity", 1.0)))
        self.dsp_smoothing.setValue(float(cfg.get("steering_smoothing_alpha", 0.15)))
        self.cb_invert.setChecked(bool(cfg.get("steering_inversion", False)))

    def reset_to_defaults(self) -> None:
        """Reset steering controls to factory defaults."""
        self.sb_max_angle.setValue(30)
        self.dsp_deadzone.setValue(0.05)
        self.dsp_sensitivity.setValue(1.0)
        self.dsp_smoothing.setValue(0.15)
        self.cb_invert.setChecked(False)


class ControllerPage(QWidget):
    """Virtual Xbox Controller hardware output settings page."""

    reconnect_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._current_config = ControllerConfig()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        lbl_title = QLabel("VIRTUAL CONTROLLER SETTINGS")
        lbl_title.setObjectName("sectionTitle")
        layout.addWidget(lbl_title)

        card = QFrame()
        card.setObjectName("statusCard")
        c_layout = QFormLayout(card)
        c_layout.setContentsMargins(16, 16, 16, 16)
        c_layout.setSpacing(12)

        self.lbl_status = QLabel("● Connected (ViGEmBus)")
        self.lbl_status.setStyleSheet("color: #00e676; font-weight: 700;")

        self.combo_type = NoWheelComboBox()
        self.combo_type.addItems(["Virtual Xbox 360 Controller (ViGEmBus)", "Null Controller (Safe Mode)"])

        self.btn_reconnect = QPushButton("🔌   Reconnect Controller")
        self.btn_reconnect.setObjectName("btnStart")
        self.btn_reconnect.clicked.connect(self.reconnect_requested.emit)

        c_layout.addRow("Hardware Status:", self.lbl_status)
        c_layout.addRow("Controller Emulation:", self.combo_type)
        c_layout.addRow(self.btn_reconnect)

        layout.addWidget(card)

        # Output Gauges Preview Card
        gauge_card = QFrame()
        gauge_card.setObjectName("statusCard")
        g_layout = QVBoxLayout(gauge_card)
        g_layout.setContentsMargins(14, 12, 14, 12)
        g_layout.setSpacing(8)

        lbl_g_title = QLabel("LIVE STICK OUTPUT PREVIEW:")
        lbl_g_title.setStyleSheet("color: #8f96a3; font-size: 11px; font-weight: 600;")
        g_layout.addWidget(lbl_g_title)

        self.pb_stick = QProgressBar()
        self.pb_stick.setRange(-32768, 32767)
        self.pb_stick.setValue(0)
        self.pb_stick.setFormat("Left Stick X: %v")
        g_layout.addWidget(self.pb_stick)

        layout.addWidget(gauge_card)
        layout.addStretch()

    def get_config(self) -> ControllerConfig:
        emu = "null" if self.combo_type.currentIndex() == 1 else "xbox"
        return ControllerConfig(
            emulation_type=emu,
            rumble_enabled=self._current_config.rumble_enabled,
            deadzone=self._current_config.deadzone,
            trigger_min=self._current_config.trigger_min,
            trigger_max=self._current_config.trigger_max,
            stick_min=self._current_config.stick_min,
            stick_max=self._current_config.stick_max,
            update_frequency=self._current_config.update_frequency,
        )

    def set_config(self, cfg: dict | ControllerConfig) -> None:
        if not cfg:
            return
        if hasattr(cfg, "to_dict"):
            cfg = cfg.to_dict()
        self._current_config = ControllerConfig.from_dict(cfg)
        emu = self._current_config.emulation_type
        idx = 1 if str(emu).lower() == "null" else 0
        self.combo_type.setCurrentIndex(idx)

    def reset_to_defaults(self) -> None:
        self._current_config = ControllerConfig()
        self.combo_type.setCurrentIndex(0)


class CalibrationPage(QWidget):
    """Calibration status, wizard launcher, and export/import page."""

    open_wizard_requested = Signal()
    reset_calibration_requested = Signal()

    def __init__(self, calibration_manager: CalibrationManager, parent=None) -> None:
        super().__init__(parent)
        self.manager = calibration_manager

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        lbl_title = QLabel("STEERING CALIBRATION MANAGEMENT")
        lbl_title.setObjectName("sectionTitle")
        layout.addWidget(lbl_title)

        card = QFrame()
        card.setObjectName("statusCard")
        c_layout = QFormLayout(card)
        c_layout.setContentsMargins(16, 16, 16, 16)
        c_layout.setSpacing(12)

        self.lbl_cal_status = QLabel("● Loaded")
        self.lbl_cal_status.setStyleSheet("color: #00e676; font-weight: 700;")

        self.lbl_cal_file = QLabel(str(get_default_calibration_path()))
        self.lbl_cal_file.setStyleSheet("color: #8f96a3;")

        c_layout.addRow("Calibration Status:", self.lbl_cal_status)
        c_layout.addRow("Profile File:", self.lbl_cal_file)

        layout.addWidget(card)

        # Buttons Card
        btn_card = QFrame()
        btn_card.setObjectName("statusCard")
        b_layout = QVBoxLayout(btn_card)
        b_layout.setContentsMargins(16, 16, 16, 16)
        b_layout.setSpacing(10)

        self.btn_wizard = QPushButton("🎯   Open Calibration Wizard")
        self.btn_wizard.setObjectName("btnStart")
        self.btn_wizard.clicked.connect(self.open_wizard_requested.emit)

        self.btn_reset = QPushButton("🔄   Reset to Default Configuration")
        self.btn_reset.setObjectName("btnStop")
        self.btn_reset.clicked.connect(self.reset_calibration_requested.emit)

        exp_imp_box = QHBoxLayout()
        exp_imp_box.setSpacing(10)

        self.btn_export = QPushButton("📤   Export Calibration JSON")
        self.btn_export.clicked.connect(self._on_export)

        self.btn_import = QPushButton("📥   Import Calibration JSON")
        self.btn_import.clicked.connect(self._on_import)

        exp_imp_box.addWidget(self.btn_export)
        exp_imp_box.addWidget(self.btn_import)

        b_layout.addWidget(self.btn_wizard)
        b_layout.addWidget(self.btn_reset)
        b_layout.addLayout(exp_imp_box)

        layout.addWidget(btn_card)
        layout.addStretch()

    def update_status(self) -> None:
        """Update calibration status display."""
        active = self.manager.active_calibration is not None
        if active:
            self.lbl_cal_status.setText("● Loaded")
            self.lbl_cal_status.setStyleSheet("color: #00e676; font-weight: 700;")
        else:
            self.lbl_cal_status.setText("● Default Configuration")
            self.lbl_cal_status.setStyleSheet("color: #ffb300; font-weight: 700;")

    def _on_export(self) -> None:
        filePath, _ = QFileDialog.getSaveFileName(
            self, "Export Calibration JSON", str(get_user_profiles_dir() / "exported_calibration.json"), "JSON Files (*.json)"
        )
        if filePath:
            try:
                data = self.manager.active_calibration
                if data:
                    with open(filePath, "w") as f:
                        f.write(data.to_json())
                    QMessageBox.information(self, "Export Successful", f"Calibration exported to:\n{filePath}")
                else:
                    QMessageBox.warning(self, "Export Warning", "No active calibration to export.")
            except Exception as exc:
                QMessageBox.critical(self, "Export Error", f"Failed to export calibration: {exc}")

    def _on_import(self) -> None:
        filePath, _ = QFileDialog.getOpenFileName(
            self, "Import Calibration JSON", str(get_user_profiles_dir()), "JSON Files (*.json)"
        )
        if filePath:
            try:
                from calibration.calibration_data import CalibrationData
                with open(filePath, "r") as f:
                    data = CalibrationData.from_json(f.read())
                self.manager.save_calibration(data)
                self.update_status()
                QMessageBox.information(self, "Import Successful", "Calibration imported and applied live!")
            except Exception as exc:
                QMessageBox.critical(self, "Import Error", f"Failed to import calibration: {exc}")


class ProfilePage(QWidget):
    """Driving & Desktop Profile Management page with complete CRUD operations."""

    profile_switched = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._profile_manager = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        lbl_title = QLabel("PROFILE MANAGEMENT")
        lbl_title.setObjectName("sectionTitle")
        layout.addWidget(lbl_title)

        card = QFrame()
        card.setObjectName("statusCard")
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(16, 16, 16, 16)
        c_layout.setSpacing(12)

        self.lbl_active = QLabel("Active Profile: Default")
        self.lbl_active.setStyleSheet("color: #00e5ff; font-weight: 700; font-size: 15px;")
        c_layout.addWidget(self.lbl_active)

        self.list_profiles = QListWidget()
        self.list_profiles.setStyleSheet(
            "QListWidget { background-color: #12141d; gridline-color: #1e2230; border: 1px solid #282c3c; border-radius: 6px; padding: 4px; }"
            "QListWidget::item { padding: 8px; border-bottom: 1px solid #1a1d28; color: #ffffff; font-size: 12px; }"
            "QListWidget::item:selected { background-color: #282c3c; color: #00e5ff; font-weight: bold; border-radius: 4px; }"
        )
        c_layout.addWidget(self.list_profiles)

        # Action Buttons Toolbar
        grid_btn = QGridLayout()
        grid_btn.setSpacing(8)

        self.btn_switch = QPushButton("✔   Set Active")
        self.btn_switch.setObjectName("btnStart")
        self.btn_switch.clicked.connect(self._on_switch)

        self.btn_create = QPushButton("➕   New Profile")
        self.btn_create.clicked.connect(self._on_create)

        self.btn_rename = QPushButton("✏️   Rename")
        self.btn_rename.clicked.connect(self._on_rename)

        self.btn_duplicate = QPushButton("📋   Duplicate")
        self.btn_duplicate.clicked.connect(self._on_duplicate)

        self.btn_delete = QPushButton("🗑️   Delete")
        self.btn_delete.setStyleSheet(
            "QPushButton { background-color: #2b1f24; color: #ff5252; border: 1px solid #ff5252; border-radius: 6px; padding: 6px 12px; font-weight: bold; font-size: 12px; }"
            "QPushButton:hover { background-color: #ff5252; color: #ffffff; }"
        )
        self.btn_delete.clicked.connect(self._on_delete)

        self.btn_import = QPushButton("📥   Import JSON")
        self.btn_import.clicked.connect(self._on_import)

        self.btn_export = QPushButton("📤   Export JSON")
        self.btn_export.clicked.connect(self._on_export)

        self.btn_restore = QPushButton("🔄   Restore Default")
        self.btn_restore.clicked.connect(self._on_restore_default)

        # Grid row 0: Main actions
        grid_btn.addWidget(self.btn_switch, 0, 0)
        grid_btn.addWidget(self.btn_create, 0, 1)
        grid_btn.addWidget(self.btn_rename, 0, 2)
        grid_btn.addWidget(self.btn_duplicate, 0, 3)

        # Grid row 1: Management actions
        grid_btn.addWidget(self.btn_import, 1, 0)
        grid_btn.addWidget(self.btn_export, 1, 1)
        grid_btn.addWidget(self.btn_restore, 1, 2)
        grid_btn.addWidget(self.btn_delete, 1, 3)

        c_layout.addLayout(grid_btn)
        layout.addWidget(card)
        layout.addStretch()

    def set_profile_manager(self, pm) -> None:
        """Connect ProfileManager and populate profile list."""
        self._profile_manager = pm
        self.refresh_profiles()

    def _get_selected_name(self) -> Optional[str]:
        item = self.list_profiles.currentItem()
        if item:
            # Extract plain profile name stored in Qt UserRole
            name = item.data(Qt.UserRole)
            if name:
                return name
            # Fallback parsing first line of text
            txt = item.text().split("\n")[0].replace("  [ACTIVE]", "").strip()
            return txt
        return None

    def refresh_profiles(self) -> None:
        """Refresh profile list from ProfileManager with rich metadata details."""
        self.list_profiles.clear()
        if not self._profile_manager:
            self.lbl_active.setText("Active Profile: Default")
            item = QListWidgetItem("Default\n  Created: N/A  |  Calibration: Default")
            item.setData(Qt.UserRole, "Default")
            self.list_profiles.addItem(item)
            return

        active_name = self._profile_manager.active_name
        self.lbl_active.setText(f"Active Profile: {active_name}")

        profiles = self._profile_manager.list_profiles()
        selected_idx = 0
        for idx, p in enumerate(profiles):
            is_active = (p.name == active_name)
            badge = "  [ACTIVE]" if is_active else ""
            cal_str = "🎯 Calibrated" if p.is_calibrated else "⚠️ Uncalibrated"
            created_str = p.metadata.created_at[:10] if p.metadata.created_at else "N/A"
            modified_str = p.metadata.modified_at[:10] if p.metadata.modified_at else "N/A"

            displayText = f"{p.name}{badge}\n  Created: {created_str}  |  Modified: {modified_str}  |  {cal_str}"
            item = QListWidgetItem(displayText)
            item.setData(Qt.UserRole, p.name)
            if is_active:
                item.setForeground(QColor("#00e5ff"))
                selected_idx = idx

            self.list_profiles.addItem(item)

        if self.list_profiles.count() > 0:
            self.list_profiles.setCurrentRow(selected_idx)

    def _on_switch(self) -> None:
        name = self._get_selected_name()
        if not name:
            QMessageBox.warning(self, "Profile Error", "Please select a profile from the list.")
            return

        if self._profile_manager:
            try:
                self._profile_manager.set_active(name)
                self.refresh_profiles()
                self.profile_switched.emit(name)
                QMessageBox.information(self, "Profile Switched", f"Active profile set to: {name}")
            except Exception as exc:
                QMessageBox.warning(self, "Switch Error", f"Could not switch profile: {exc}")

    def _on_create(self) -> None:
        from PySide6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "Create New Profile", "Enter new profile name:")
        if ok and name.strip():
            clean_name = name.strip()
            if self._profile_manager:
                try:
                    self._profile_manager.create(clean_name)
                    self.refresh_profiles()
                    QMessageBox.information(self, "Profile Created", f"Created new profile '{clean_name}'.")
                except Exception as exc:
                    QMessageBox.warning(self, "Create Error", f"Could not create profile: {exc}")

    def _on_rename(self) -> None:
        old_name = self._get_selected_name()
        if not old_name:
            QMessageBox.warning(self, "Profile Error", "Please select a profile to rename.")
            return

        from PySide6.QtWidgets import QInputDialog
        new_name, ok = QInputDialog.getText(self, "Rename Profile", f"Enter new name for profile '{old_name}':", text=old_name)
        if ok and new_name.strip() and new_name.strip() != old_name:
            clean_new = new_name.strip()
            if self._profile_manager:
                try:
                    self._profile_manager.rename(old_name, clean_new)
                    self.refresh_profiles()
                    self.profile_switched.emit(clean_new)
                    QMessageBox.information(self, "Profile Renamed", f"Renamed profile '{old_name}' → '{clean_new}'.")
                except Exception as exc:
                    QMessageBox.warning(self, "Rename Error", f"Could not rename profile: {exc}")

    def _on_duplicate(self) -> None:
        src_name = self._get_selected_name()
        if not src_name:
            QMessageBox.warning(self, "Profile Error", "Please select a profile to duplicate.")
            return

        from PySide6.QtWidgets import QInputDialog
        copy_name, ok = QInputDialog.getText(self, "Duplicate Profile", f"Enter name for duplicate copy of '{src_name}':", text=f"{src_name} Copy")
        if ok and copy_name.strip():
            clean_copy = copy_name.strip()
            if self._profile_manager:
                try:
                    self._profile_manager.duplicate(src_name, clean_copy)
                    self.refresh_profiles()
                    QMessageBox.information(self, "Profile Duplicated", f"Duplicated profile '{src_name}' → '{clean_copy}'.")
                except Exception as exc:
                    QMessageBox.warning(self, "Duplicate Error", f"Could not duplicate profile: {exc}")

    def _on_delete(self) -> None:
        target_name = self._get_selected_name()
        if not target_name:
            QMessageBox.warning(self, "Profile Error", "Please select a profile to delete.")
            return

        active_name = self._profile_manager.active_name if self._profile_manager else ""
        if target_name == active_name:
            QMessageBox.warning(
                self,
                "Cannot Delete Active Profile",
                f"Profile '{target_name}' is currently active.\n\nPlease select and activate another profile first before deleting this one.",
            )
            return

        reply = QMessageBox.question(
            self,
            "Delete Profile",
            f"Are you sure you want to permanently delete profile '{target_name}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes and self._profile_manager:
            try:
                self._profile_manager.delete(target_name)
                self.refresh_profiles()
                QMessageBox.information(self, "Profile Deleted", f"Deleted profile '{target_name}'.")
            except Exception as exc:
                QMessageBox.warning(self, "Delete Error", f"Could not delete profile: {exc}")

    def _on_import(self) -> None:
        filePath, _ = QFileDialog.getOpenFileName(
            self, "Import Profile JSON", str(get_user_profiles_dir()), "JSON Files (*.json)"
        )
        if filePath and self._profile_manager:
            try:
                from pathlib import Path
                p = self._profile_manager.import_profile(Path(filePath))
                self.refresh_profiles()
                QMessageBox.information(self, "Import Successful", f"Successfully imported profile '{p.name}'!")
            except Exception as exc:
                QMessageBox.critical(self, "Import Error", f"Failed to import profile:\n{exc}")

    def _on_export(self) -> None:
        target_name = self._get_selected_name()
        if not target_name:
            QMessageBox.warning(self, "Profile Error", "Please select a profile to export.")
            return

        destPath, _ = QFileDialog.getSaveFileName(
            self, "Export Profile JSON", str(get_user_profiles_dir() / f"exported_{target_name.lower().replace(' ', '_')}.json"), "JSON Files (*.json)"
        )
        if destPath and self._profile_manager:
            try:
                from pathlib import Path
                self._profile_manager.export_profile(target_name, Path(destPath))
                QMessageBox.information(self, "Export Successful", f"Profile '{target_name}' exported to:\n{destPath}")
            except Exception as exc:
                QMessageBox.critical(self, "Export Error", f"Failed to export profile:\n{exc}")

    def _on_restore_default(self) -> None:
        target_name = self._get_selected_name()
        if not target_name:
            QMessageBox.warning(self, "Profile Error", "Please select a profile to restore.")
            return

        reply = QMessageBox.question(
            self,
            "Restore Factory Defaults",
            f"Are you sure you want to reset profile '{target_name}' to factory default settings?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes and self._profile_manager:
            try:
                self._profile_manager.restore_default(target_name)
                self.refresh_profiles()
                if target_name == self._profile_manager.active_name:
                    self.profile_switched.emit(target_name)
                QMessageBox.information(self, "Restore Successful", f"Profile '{target_name}' restored to factory defaults.")
            except Exception as exc:
                QMessageBox.warning(self, "Restore Error", f"Could not restore profile defaults: {exc}")


class AboutPage(QWidget):
    """Application metadata and about information page."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        lbl_title = QLabel("ABOUT DRIVEBYGESTURE")
        lbl_title.setObjectName("sectionTitle")
        layout.addWidget(lbl_title)

        card = QFrame()
        card.setObjectName("statusCard")
        c_layout = QFormLayout(card)
        c_layout.setContentsMargins(16, 16, 16, 16)
        c_layout.setSpacing(12)

        py_ver = sys.version.split()[0]
        qt_ver = PySide6.__version__
        mp_ver = getattr(mp, "__version__", "0.10.x")

        c_layout.addRow("Application:", QLabel("DriveByGesture Control Center"))
        c_layout.addRow("Version:", QLabel("1.0.0 (Phase 9 Release)"))
        c_layout.addRow("Author:", QLabel("Google DeepMind Team & User Pair Programmed"))
        c_layout.addRow("Python Runtime:", QLabel(py_ver))
        c_layout.addRow("PySide6 / Qt:", QLabel(qt_ver))
        c_layout.addRow("MediaPipe Version:", QLabel(mp_ver))
        c_layout.addRow("ViGEmBus Status:", QLabel("Active / Emulated"))
        c_layout.addRow("GitHub Repository:", QLabel("https://github.com/adhil-vt/DriveByGesture"))
        c_layout.addRow("License:", QLabel("MIT License"))

        self.btn_open_help = QPushButton("📖   Open Complete Help Center")
        self.btn_open_help.setObjectName("btnStart")
        self.btn_open_help.clicked.connect(self._on_open_help)
        c_layout.addRow("Documentation:", self.btn_open_help)

        layout.addWidget(card)
        layout.addStretch()

    def _on_open_help(self) -> None:
        if self.parent() and hasattr(self.parent(), "parent") and self.parent().parent():
            main_win = self.parent().parent()
            if hasattr(main_win, "open_help_center"):
                main_win.open_help_center()
                return
        from gui.help_dialog import HelpCenterDialog
        dialog = HelpCenterDialog(self)
        dialog.exec()


def get_implemented_gestures() -> list[str]:
    """Dynamically query implemented gestures from gesture recognition system."""
    try:
        from gestures.builtins import (
            FistGesture,
            OpenPalmGesture,
            PeaceGesture,
            PinchGesture,
            PinchPinkyGesture,
            PointGesture,
            ThumbsUpGesture,
        )
        gestures = [
            OpenPalmGesture(),
            PinchGesture(),
            PinchPinkyGesture(),
            PeaceGesture(),
            PointGesture(),
            FistGesture(),
            ThumbsUpGesture(),
        ]
        return [g.name for g in gestures]
    except Exception:
        return ["Open Palm", "Pinch", "Pinch Pinky", "Peace", "Point", "Fist", "Thumbs Up", "Thumbs Down"]


class DesktopControlsPage(QWidget):
    """
    Dedicated Desktop Controls settings page for Desktop Gesture Mode.
    Provides a scrollable, responsive UI layout with compact cards for cursor tuning,
    gesture bindings, keyboard shortcuts, live monitoring, and control resets.
    """

    DESKTOP_ACTIONS = [
        ("MOVE_CURSOR", "Move Cursor", "Open Palm"),
        ("LEFT_CLICK", "Left Click", "Pinch"),
        ("RIGHT_CLICK", "Right Click", "Peace"),
        ("DOUBLE_CLICK", "Double Click", "Point"),
        ("DRAG", "Drag (Hold)", "Fist"),
        ("SCROLL_UP", "Scroll Up", "None"),
        ("SCROLL_DOWN", "Scroll Down", "None"),
        ("VOLUME_UP", "Volume Up", "Thumbs Up"),
        ("VOLUME_DOWN", "Volume Down", "Thumbs Down"),
        ("MUTE", "Mute Volume", "None"),
        ("PLAY_PAUSE", "Play / Pause", "None"),
        ("NEXT_TRACK", "Next Track", "None"),
        ("PREV_TRACK", "Previous Track", "None"),
        ("SHOW_DESKTOP", "Show Desktop", "None"),
        ("TASK_VIEW", "Task View", "None"),
        ("CUSTOM_SHORTCUT", "Custom Shortcut", "None"),
    ]

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(0)

        # ── Scroll Area Container ──────────────────────────────────────────
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setStyleSheet(
            "QScrollArea { background-color: transparent; border: none; }"
            "QScrollBar:vertical { background-color: #0d0e12; width: 8px; border-radius: 4px; }"
            "QScrollBar::handle:vertical { background-color: #282c3c; border-radius: 4px; min-height: 20px; }"
            "QScrollBar::handle:vertical:hover { background-color: #00e5ff; }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }"
        )

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(14, 14, 14, 14)
        scroll_layout.setSpacing(12)

        lbl_title = QLabel("DESKTOP MODE CONTROLS & BINDINGS")
        lbl_title.setObjectName("sectionTitle")
        scroll_layout.addWidget(lbl_title)

        # ── 0. Available Gestures Section (Compact Chips) ──────────────────
        card_gestures = QFrame()
        card_gestures.setObjectName("statusCard")
        g_chip_layout = QVBoxLayout(card_gestures)
        g_chip_layout.setContentsMargins(12, 10, 12, 10)
        g_chip_layout.setSpacing(6)

        lbl_g_header = QLabel("AVAILABLE GESTURES")
        lbl_g_header.setStyleSheet("color: #00e5ff; font-weight: 700; font-size: 11px;")
        g_chip_layout.addWidget(lbl_g_header)

        chips_flow = QHBoxLayout()
        chips_flow.setSpacing(6)
        chips_flow.setAlignment(Qt.AlignLeft)

        self._available_gestures_list = get_implemented_gestures()
        for g_name in self._available_gestures_list:
            lbl_chip = QLabel(f"👋 {g_name}")
            lbl_chip.setStyleSheet(
                "background-color: #1a1d28; color: #00e5ff; border: 1px solid #282c3c; "
                "border-radius: 10px; padding: 3px 8px; font-weight: bold; font-size: 11px;"
            )
            chips_flow.addWidget(lbl_chip)

        g_chip_layout.addLayout(chips_flow)
        scroll_layout.addWidget(card_gestures)

        # ── 1. Cursor Settings Card (Compact) ─────────────────────────────
        card_cursor = QFrame()
        card_cursor.setObjectName("statusCard")
        c_layout = QFormLayout(card_cursor)
        c_layout.setContentsMargins(12, 10, 12, 10)
        c_layout.setSpacing(8)

        lbl_c_header = QLabel("CURSOR SETTINGS")
        lbl_c_header.setStyleSheet("color: #00e5ff; font-weight: 700; font-size: 11px;")
        c_layout.addRow(lbl_c_header)

        self.combo_mode = NoWheelComboBox()
        self.combo_mode.addItem("🚗 Driving Mode", "driving")
        self.combo_mode.addItem("🖥️ Desktop Mode", "desktop")

        # Sensitivity (Slider + DoubleSpinBox)
        sens_box = QHBoxLayout()
        self.slider_sensitivity = NoWheelSlider(Qt.Horizontal)
        self.slider_sensitivity.setRange(20, 500)
        self.slider_sensitivity.setValue(175)
        self.dsp_sensitivity = NoWheelDoubleSpinBox()
        self.dsp_sensitivity.setRange(0.2, 5.0)
        self.dsp_sensitivity.setSingleStep(0.1)
        self.dsp_sensitivity.setValue(1.75)
        sens_box.addWidget(self.slider_sensitivity, stretch=1)
        sens_box.addWidget(self.dsp_sensitivity)
        self.slider_sensitivity.valueChanged.connect(lambda v: self.dsp_sensitivity.setValue(v / 100.0))
        self.dsp_sensitivity.valueChanged.connect(lambda v: self.slider_sensitivity.setValue(int(v * 100)))

        # Smoothing (Slider + DoubleSpinBox)
        smooth_box = QHBoxLayout()
        self.slider_smoothing = NoWheelSlider(Qt.Horizontal)
        self.slider_smoothing.setRange(5, 100)
        self.slider_smoothing.setValue(25)
        self.dsp_smoothing = NoWheelDoubleSpinBox()
        self.dsp_smoothing.setRange(0.05, 1.0)
        self.dsp_smoothing.setSingleStep(0.05)
        self.dsp_smoothing.setValue(0.25)
        smooth_box.addWidget(self.slider_smoothing, stretch=1)
        smooth_box.addWidget(self.dsp_smoothing)
        self.slider_smoothing.valueChanged.connect(lambda v: self.dsp_smoothing.setValue(v / 100.0))
        self.dsp_smoothing.valueChanged.connect(lambda v: self.slider_smoothing.setValue(int(v * 100)))

        # Dead Zone (Slider + DoubleSpinBox)
        dz_box = QHBoxLayout()
        self.slider_deadzone = NoWheelSlider(Qt.Horizontal)
        self.slider_deadzone.setRange(0, 30)
        self.slider_deadzone.setValue(5)
        self.dsp_deadzone = NoWheelDoubleSpinBox()
        self.dsp_deadzone.setRange(0.0, 0.30)
        self.dsp_deadzone.setSingleStep(0.01)
        self.dsp_deadzone.setValue(0.05)
        dz_box.addWidget(self.slider_deadzone, stretch=1)
        dz_box.addWidget(self.dsp_deadzone)
        self.slider_deadzone.valueChanged.connect(lambda v: self.dsp_deadzone.setValue(v / 100.0))
        self.dsp_deadzone.valueChanged.connect(lambda v: self.slider_deadzone.setValue(int(v * 100)))

        # Checkboxes in single compact row
        chk_row = QHBoxLayout()
        chk_row.setSpacing(16)
        self.cb_cursor_enabled = QCheckBox("Enable Cursor Movement")
        self.cb_cursor_enabled.setChecked(True)
        self.cb_invert_x = QCheckBox("Invert X")
        self.cb_invert_x.setChecked(False)
        self.cb_invert_y = QCheckBox("Invert Y")
        self.cb_invert_y.setChecked(False)
        chk_row.addWidget(self.cb_cursor_enabled)
        chk_row.addWidget(self.cb_invert_x)
        chk_row.addWidget(self.cb_invert_y)
        chk_row.addStretch()

        c_layout.addRow("Operating Mode:", self.combo_mode)
        c_layout.addRow("Cursor Sensitivity:", sens_box)
        c_layout.addRow("Cursor Smoothing:", smooth_box)
        c_layout.addRow("Dead Zone:", dz_box)
        c_layout.addRow(chk_row)

        scroll_layout.addWidget(card_cursor)

        # ── 1b. Workspace & Calibration Card ──────────────────────────────
        card_ws = QFrame()
        card_ws.setObjectName("statusCard")
        ws_layout = QFormLayout(card_ws)
        ws_layout.setContentsMargins(16, 12, 16, 12)
        ws_layout.setSpacing(10)

        lbl_ws_header = QLabel("WORKSPACE & CALIBRATION")
        lbl_ws_header.setStyleSheet("color: #00e5ff; font-weight: 700; font-size: 11px;")
        ws_layout.addRow(lbl_ws_header)

        # Horizontal Workspace % (Slider + SpinBox)
        ws_h_box = QHBoxLayout()
        self.slider_ws_w = NoWheelSlider(Qt.Horizontal)
        self.slider_ws_w.setRange(50, 100)
        self.slider_ws_w.setValue(80)
        self.dsp_ws_w = NoWheelSpinBox()
        self.dsp_ws_w.setRange(50, 100)
        self.dsp_ws_w.setSuffix("%")
        self.dsp_ws_w.setValue(80)
        ws_h_box.addWidget(self.slider_ws_w, stretch=1)
        ws_h_box.addWidget(self.dsp_ws_w)
        self.slider_ws_w.valueChanged.connect(self.dsp_ws_w.setValue)
        self.dsp_ws_w.valueChanged.connect(self.slider_ws_w.setValue)

        # Vertical Workspace % (Slider + SpinBox)
        ws_v_box = QHBoxLayout()
        self.slider_ws_h = NoWheelSlider(Qt.Horizontal)
        self.slider_ws_h.setRange(50, 100)
        self.slider_ws_h.setValue(80)
        self.dsp_ws_h = NoWheelSpinBox()
        self.dsp_ws_h.setRange(50, 100)
        self.dsp_ws_h.setSuffix("%")
        self.dsp_ws_h.setValue(80)
        ws_v_box.addWidget(self.slider_ws_h, stretch=1)
        ws_v_box.addWidget(self.dsp_ws_h)
        self.slider_ws_h.valueChanged.connect(self.dsp_ws_h.setValue)
        self.dsp_ws_h.valueChanged.connect(self.slider_ws_h.setValue)

        # Checkbox: Workspace Overlay
        self.cb_show_ws_overlay = QCheckBox("Draw Active Workspace Overlay on Camera Preview")
        self.cb_show_ws_overlay.setChecked(True)

        ws_layout.addRow("Horizontal Workspace:", ws_h_box)
        ws_layout.addRow("Vertical Workspace:", ws_v_box)
        ws_layout.addRow(self.cb_show_ws_overlay)

        scroll_layout.addWidget(card_ws)

        # ── 2. Gesture Bindings Table Card (Primary) ─────────────────────
        card_table = QFrame()
        card_table.setObjectName("statusCard")
        t_layout = QVBoxLayout(card_table)
        t_layout.setContentsMargins(12, 10, 12, 10)
        t_layout.setSpacing(6)

        lbl_t_header = QLabel("GESTURE BINDINGS")
        lbl_t_header.setStyleSheet("color: #00e5ff; font-weight: 700; font-size: 11px;")
        t_layout.addWidget(lbl_t_header)

        self.table_bindings = QTableWidget()
        self.table_bindings.setColumnCount(4)
        self.table_bindings.setHorizontalHeaderLabels(["Action", "Gesture", "Enabled", "Edit"])
        self.table_bindings.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table_bindings.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table_bindings.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table_bindings.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table_bindings.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_bindings.setMinimumHeight(280)
        self.table_bindings.setStyleSheet(
            "QTableWidget { background-color: #0d0e12; gridline-color: #282c3c; border-radius: 6px; border: 1px solid #282c3c; }"
            "QHeaderView::section { background-color: #1a1d28; color: #00e5ff; padding: 6px; font-weight: bold; border: 1px solid #282c3c; }"
            "QTableWidget::item { padding: 4px; color: #e0e0e0; }"
        )

        self._available_gestures = ["None"] + self._available_gestures_list
        self._action_rows = {}

        self.table_bindings.setRowCount(len(self.DESKTOP_ACTIONS))
        for row, (act_key, act_label, default_gesture) in enumerate(self.DESKTOP_ACTIONS):
            self._action_rows[act_key] = row

            # Col 0: Action
            item_action = QTableWidgetItem(act_label)
            item_action.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.table_bindings.setItem(row, 0, item_action)

            # Col 1: Gesture
            item_gesture = QTableWidgetItem(default_gesture)
            item_gesture.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            item_gesture.setTextAlignment(Qt.AlignCenter)
            self.table_bindings.setItem(row, 1, item_gesture)

            # Col 2: Enabled Checkbox
            chk = QCheckBox()
            chk.setChecked(True)
            cell_widget = QWidget()
            chk_layout = QHBoxLayout(cell_widget)
            chk_layout.addWidget(chk)
            chk_layout.setAlignment(Qt.AlignCenter)
            chk_layout.setContentsMargins(0, 0, 0, 0)
            self.table_bindings.setCellWidget(row, 2, cell_widget)

            # Col 3: Edit Combo Box (Populated dynamically)
            combo = NoWheelComboBox()
            combo.addItems(self._available_gestures)
            if default_gesture in self._available_gestures:
                combo.setCurrentText(default_gesture)
            else:
                combo.setCurrentText("None")

            def _make_combo_cb(r=row, c=combo):
                return lambda idx: self.table_bindings.item(r, 1).setText(c.currentText())

            combo.currentIndexChanged.connect(_make_combo_cb(row, combo))
            self.table_bindings.setCellWidget(row, 3, combo)

        t_layout.addWidget(self.table_bindings)
        scroll_layout.addWidget(card_table)

        # ── 3. Keyboard Shortcuts Card ──────────────────────────────────────
        card_shortcuts = QFrame()
        card_shortcuts.setObjectName("statusCard")
        s_layout = QVBoxLayout(card_shortcuts)
        s_layout.setContentsMargins(12, 10, 12, 10)
        s_layout.setSpacing(6)

        lbl_s_header = QLabel("KEYBOARD SHORTCUTS")
        lbl_s_header.setStyleSheet("color: #00e5ff; font-weight: 700; font-size: 11px;")
        s_layout.addWidget(lbl_s_header)

        s_form = QFormLayout()
        s_form.setSpacing(6)
        self.txt_shortcut = QLineEdit("ctrl+tab")
        self.txt_shortcut.setPlaceholderText("e.g. ctrl+c, win+d, alt+tab, ctrl+shift+esc")
        s_form.addRow("Custom Shortcut Sequence:", self.txt_shortcut)
        s_layout.addLayout(s_form)

        preset_box = QHBoxLayout()
        preset_box.setSpacing(6)
        preset_box.setAlignment(Qt.AlignLeft)
        presets = ["Ctrl+C", "Ctrl+V", "Ctrl+Z", "Win+D", "Alt+Tab", "Ctrl+Shift+Esc"]
        for p in presets:
            btn = QPushButton(p)
            btn.setStyleSheet(
                "QPushButton { background-color: #1a1d28; color: #00e5ff; border: 1px solid #282c3c; border-radius: 4px; padding: 3px 8px; font-weight: bold; font-size: 11px; }"
                "QPushButton:hover { background-color: #282c3c; color: #ffffff; }"
            )
            btn.clicked.connect(lambda _, key=p.lower(): self.txt_shortcut.setText(key))
            preset_box.addWidget(btn)
        s_layout.addLayout(preset_box)
        scroll_layout.addWidget(card_shortcuts)

        # ── 4. Live Monitor Card ───────────────────────────────────────────
        card_test = QFrame()
        card_test.setObjectName("statusCard")
        test_layout = QVBoxLayout(card_test)
        test_layout.setContentsMargins(12, 10, 12, 10)
        test_layout.setSpacing(6)

        lbl_test_header = QLabel("LIVE MONITOR")
        lbl_test_header.setStyleSheet("color: #00e5ff; font-weight: 700; font-size: 11px;")
        test_layout.addWidget(lbl_test_header)

        grid_test = QGridLayout()
        grid_test.setSpacing(6)

        lbl_g_tag = QLabel("Current Gesture:")
        lbl_g_tag.setStyleSheet("color: #8f96a3; font-weight: 600;")
        self.lbl_test_gesture = QLabel("[ None ]")
        self.lbl_test_gesture.setStyleSheet("color: #ffb300; font-weight: 700; font-size: 12px;")

        lbl_a_tag = QLabel("Current Action:")
        lbl_a_tag.setStyleSheet("color: #8f96a3; font-weight: 600;")
        self.lbl_test_action = QLabel("Idle")
        self.lbl_test_action.setStyleSheet("color: #00e676; font-weight: 700; font-size: 12px;")

        lbl_c_tag = QLabel("Confidence:")
        lbl_c_tag.setStyleSheet("color: #8f96a3; font-weight: 600;")
        self.lbl_test_confidence = QLabel("N/A")
        self.lbl_test_confidence.setStyleSheet("color: #ffffff; font-weight: 700;")

        lbl_s_tag = QLabel("Status:")
        lbl_s_tag.setStyleSheet("color: #8f96a3; font-weight: 600;")
        self.lbl_test_status = QLabel("Standby")
        self.lbl_test_status.setStyleSheet("color: #8f96a3; font-weight: 700;")

        grid_test.addWidget(lbl_g_tag, 0, 0)
        grid_test.addWidget(self.lbl_test_gesture, 0, 1)
        grid_test.addWidget(lbl_a_tag, 0, 2)
        grid_test.addWidget(self.lbl_test_action, 0, 3)
        grid_test.addWidget(lbl_c_tag, 1, 0)
        grid_test.addWidget(self.lbl_test_confidence, 1, 1)
        grid_test.addWidget(lbl_s_tag, 1, 2)
        grid_test.addWidget(self.lbl_test_status, 1, 3)

        test_layout.addLayout(grid_test)
        scroll_layout.addWidget(card_test)

        # ── 5. Reset Button (Left-Aligned below cards) ───────────────────
        bar_reset = QHBoxLayout()
        bar_reset.setAlignment(Qt.AlignLeft)
        self.btn_reset_desktop = QPushButton("🔄   Reset Desktop Controls")
        self.btn_reset_desktop.setStyleSheet(
            "QPushButton { background-color: #2b1f24; color: #ff5252; border: 1px solid #ff5252; border-radius: 6px; padding: 6px 14px; font-weight: bold; font-size: 12px; }"
            "QPushButton:hover { background-color: #ff5252; color: #ffffff; }"
        )
        self.btn_reset_desktop.clicked.connect(self.reset_desktop_controls)
        bar_reset.addWidget(self.btn_reset_desktop)
        scroll_layout.addLayout(bar_reset)

        scroll_area.setWidget(scroll_content)
        page_layout.addWidget(scroll_area)

        # Keep references to hidden spinboxes if queried by existing legacy code
        self.dsp_click_delay = NoWheelDoubleSpinBox()
        self.dsp_click_delay.setValue(0.20)
        self.dsp_scroll_speed = NoWheelDoubleSpinBox()
        self.dsp_scroll_speed.setValue(1.0)
        self.dsp_cooldown = NoWheelDoubleSpinBox()
        self.dsp_cooldown.setValue(0.30)
        self.dsp_repeat_delay = NoWheelDoubleSpinBox()
        self.dsp_repeat_delay.setValue(0.50)
        self.cb_accel = QCheckBox()
        self.cb_accel.setChecked(True)

    # ── Live Telemetry Update & Row Highlight ──────────────────────────────

    def update_telemetry(self, telemetry: dict) -> None:
        """Update live testing badges and highlight active row in bindings table."""
        if not telemetry:
            return

        gesture = telemetry.get("gesture", "None")
        action = telemetry.get("desktop_action", "Idle")
        g_conf = telemetry.get("gesture_confidence", 0.0)
        active = telemetry.get("desktop_active", False)

        self.lbl_test_gesture.setText(f"[ {gesture} ]" if gesture != "None" else "[ None ]")
        self.lbl_test_action.setText(action if action != "None" else "Idle")

        if g_conf > 0.0:
            self.lbl_test_confidence.setText(f"{int(g_conf * 100)}%")
        else:
            self.lbl_test_confidence.setText("N/A")

        rejection = telemetry.get("rejection_reason", "Standby")

        if active and gesture != "None":
            self.lbl_test_status.setText("Executing")
            self.lbl_test_status.setStyleSheet("color: #00e676; font-weight: 700;")
        else:
            self.lbl_test_status.setText(rejection if rejection and rejection != "None" else "Standby")
            self.lbl_test_status.setStyleSheet("color: #ff5252; font-weight: 600;" if rejection and rejection not in ("None", "Standby", "No hand detected") else "color: #8f96a3; font-weight: 700;")

        # Live Row Highlight in Bindings Table
        target_row = -1
        if gesture != "None":
            # Find row bound to this gesture
            for row in range(self.table_bindings.rowCount()):
                cb = self.table_bindings.cellWidget(row, 3)
                if cb and cb.currentText() == gesture:
                    target_row = row
                    break

        for row in range(self.table_bindings.rowCount()):
            for col in range(2):
                item = self.table_bindings.item(row, col)
                if not item:
                    continue
                if row == target_row:
                    item.setBackground(QColor(0, 229, 255, 60))
                    item.setForeground(QColor(0, 229, 255))
                else:
                    item.setBackground(QColor(13, 14, 18))
                    item.setForeground(QColor(224, 224, 224))

    # ── Reset Controls Handler ──────────────────────────────────────────────

    def reset_desktop_controls(self) -> None:
        """Reset desktop controls and bindings to factory defaults."""
        self.dsp_sensitivity.setValue(1.75)
        self.dsp_smoothing.setValue(0.25)
        self.dsp_deadzone.setValue(0.05)
        self.cb_invert_x.setChecked(False)
        self.cb_invert_y.setChecked(False)
        self.cb_cursor_enabled.setChecked(True)
        self.dsp_click_delay.setValue(0.20)
        self.dsp_scroll_speed.setValue(1.0)
        self.dsp_cooldown.setValue(0.30)
        self.dsp_repeat_delay.setValue(0.50)
        self.cb_accel.setChecked(True)
        self.txt_shortcut.setText("ctrl+tab")

        # Reset table rows to defaults
        for act_key, act_label, default_gesture in self.DESKTOP_ACTIONS:
            row = self._action_rows.get(act_key)
            if row is not None:
                cb = self.table_bindings.cellWidget(row, 3)
                if cb:
                    if default_gesture in self._available_gestures:
                        cb.setCurrentText(default_gesture)
                    else:
                        cb.setCurrentText("None")
                cell_w = self.table_bindings.cellWidget(row, 2)
                if cell_w:
                    chk = cell_w.findChild(QCheckBox)
                    if chk:
                        chk.setChecked(True)

    # ── Configuration Serialization ────────────────────────────────────────

    def get_config(self) -> dict:
        """Export desktop settings and gesture bindings dictionary."""
        bindings = {}
        enabled_actions = {}
        for act_key, _, _ in self.DESKTOP_ACTIONS:
            row = self._action_rows.get(act_key)
            if row is not None:
                cb = self.table_bindings.cellWidget(row, 3)
                g_name = cb.currentText() if cb else "None"
                if g_name and g_name != "None":
                    bindings[g_name] = act_key

                cell_w = self.table_bindings.cellWidget(row, 2)
                chk = cell_w.findChild(QCheckBox) if cell_w else None
                enabled_actions[act_key] = chk.isChecked() if chk else True

        return {
            "mode": self.combo_mode.currentData() or "driving",
            "cursor_sensitivity": self.dsp_sensitivity.value(),
            "cursor_smoothing": self.dsp_smoothing.value(),
            "cursor_deadzone": self.dsp_deadzone.value(),
            "invert_x": self.cb_invert_x.isChecked(),
            "invert_y": self.cb_invert_y.isChecked(),
            "cursor_enabled": self.cb_cursor_enabled.isChecked(),
            "click_delay": self.dsp_click_delay.value(),
            "scroll_speed": self.dsp_scroll_speed.value(),
            "gesture_cooldown": self.dsp_cooldown.value(),
            "repeat_delay": self.dsp_repeat_delay.value(),
            "cursor_acceleration": self.cb_accel.isChecked(),
            "workspace_w_pct": self.dsp_ws_w.value() / 100.0,
            "workspace_h_pct": self.dsp_ws_h.value() / 100.0,
            "show_workspace_overlay": self.cb_show_ws_overlay.isChecked(),
            "custom_shortcut": self.txt_shortcut.text().strip(),
            "bindings": bindings,
            "enabled_actions": enabled_actions,
        }

    def set_config(self, cfg: dict) -> None:
        """Populate settings controls from desktop settings dictionary."""
        if not cfg:
            return

        self.reset_desktop_controls()

        mode_val = cfg.get("mode", "driving")
        idx = 1 if str(mode_val).lower() == "desktop" else 0
        self.combo_mode.setCurrentIndex(idx)

        self.dsp_sensitivity.setValue(float(cfg.get("cursor_sensitivity", 1.75)))
        self.dsp_smoothing.setValue(float(cfg.get("cursor_smoothing", 0.25)))
        self.dsp_deadzone.setValue(float(cfg.get("cursor_deadzone", 0.05)))
        self.cb_invert_x.setChecked(bool(cfg.get("invert_x", False)))
        self.cb_invert_y.setChecked(bool(cfg.get("invert_y", False)))
        self.cb_cursor_enabled.setChecked(bool(cfg.get("cursor_enabled", True)))
        self.dsp_click_delay.setValue(float(cfg.get("click_delay", 0.2)))
        self.dsp_scroll_speed.setValue(float(cfg.get("scroll_speed", 1.0)))
        self.dsp_cooldown.setValue(float(cfg.get("gesture_cooldown", 0.3)))
        self.dsp_repeat_delay.setValue(float(cfg.get("repeat_delay", 0.5)))
        self.cb_accel.setChecked(bool(cfg.get("cursor_acceleration", True)))
        self.dsp_ws_w.setValue(int(float(cfg.get("workspace_w_pct", 0.80)) * 100))
        self.dsp_ws_h.setValue(int(float(cfg.get("workspace_h_pct", 0.80)) * 100))
        self.cb_show_ws_overlay.setChecked(bool(cfg.get("show_workspace_overlay", True)))
        self.txt_shortcut.setText(str(cfg.get("custom_shortcut", "ctrl+tab")))

        bindings = cfg.get("bindings", {})
        enabled_actions = cfg.get("enabled_actions", {})

        # Map gesture bindings to table
        if isinstance(bindings, dict):
            for g_name, act_key in bindings.items():
                row = self._action_rows.get(act_key)
                if row is not None:
                    cb = self.table_bindings.cellWidget(row, 3)
                    if cb and g_name in self._available_gestures:
                        cb.setCurrentText(g_name)

        if isinstance(enabled_actions, dict):
            for act_key, is_en in enabled_actions.items():
                row = self._action_rows.get(act_key)
                if row is not None:
                    cell_w = self.table_bindings.cellWidget(row, 2)
                    chk = cell_w.findChild(QCheckBox) if cell_w else None
                    if chk:
                        chk.setChecked(bool(is_en))

    def update_telemetry(self, data: dict) -> None:
        """Update Live Monitor labels from real-time pipeline telemetry dictionary."""
        if not data:
            return

        gesture = data.get("gesture", "None")
        action = data.get("desktop_action", "Idle")
        state = data.get("desktop_state", "IDLE")
        conf = data.get("gesture_confidence", 0.0)
        rejection = data.get("rejection_reason", "None")
        active = data.get("desktop_active", False)

        self.lbl_test_gesture.setText(f"[ {gesture} ]")
        self.lbl_test_action.setText(action if action != "None" else "Idle")
        if isinstance(conf, (float, int)) and conf > 0.0:
            self.lbl_test_confidence.setText(f"{conf:.0%}")
        else:
            self.lbl_test_confidence.setText("N/A")

        if active and gesture != "None":
            self.lbl_test_status.setText("Executing")
            self.lbl_test_status.setStyleSheet("color: #00e676; font-weight: 700;")
        elif rejection and rejection != "None":
            self.lbl_test_status.setText(rejection)
            self.lbl_test_status.setStyleSheet("color: #ff5252; font-weight: 700;")
        else:
            self.lbl_test_status.setText("Active / Stable")
            self.lbl_test_status.setStyleSheet("color: #00e676; font-weight: 700;")


# Alias for backward compatibility
DesktopPage = DesktopControlsPage


def _section_label(text: str) -> QLabel:
    """Helper section label generator for settings pages."""
    lbl = QLabel(text)
    lbl.setObjectName("sectionTitle")
    return lbl


class AboutPage(QWidget):
    """
    Application About & System Version Information Page.
    Retrieves all values dynamically from core.version and system runtime libraries.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        from core.resources import get_app_icon
        from core.version import (
            APP_NAME,
            BUILD_DATE,
            BUILD_NUMBER,
            COMPANY,
            COPYRIGHT,
            DEVELOPER,
            LICENSE,
            RELEASE_CHANNEL,
            VERSION,
            WEBSITE,
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        layout.addWidget(_section_label("ABOUT APPLICATION"))

        # Header Branding Card
        card_brand = QFrame()
        card_brand.setObjectName("statusCard")
        cb_layout = QHBoxLayout(card_brand)
        cb_layout.setContentsMargins(20, 20, 20, 20)
        cb_layout.setSpacing(16)

        lbl_logo = QLabel()
        lbl_logo.setPixmap(get_app_icon().pixmap(64, 64))

        v_brand = QVBoxLayout()
        v_brand.setSpacing(4)

        lbl_name = QLabel(f"{APP_NAME}  v{VERSION}")
        lbl_name.setStyleSheet("font-size: 20px; font-weight: 800; color: #00e5ff;")

        lbl_desc = QLabel("Real-Time Hand-Gesture Driving Simulator & Desktop Navigator")
        lbl_desc.setStyleSheet("font-size: 13px; color: #8f96a3; font-weight: 600;")

        v_brand.addWidget(lbl_name)
        v_brand.addWidget(lbl_desc)

        cb_layout.addWidget(lbl_logo)
        cb_layout.addLayout(v_brand, stretch=1)

        layout.addWidget(card_brand)

        # Version & Runtime Metadata Table
        card_info = QFrame()
        card_info.setObjectName("statusCard")
        ci_layout = QVBoxLayout(card_info)
        ci_layout.setContentsMargins(20, 16, 20, 16)
        ci_layout.setSpacing(8)

        py_ver = sys.version.split(" ")[0]
        pyside_ver = "N/A"
        cv_ver = "N/A"
        mp_ver = "N/A"
        try:
            import PySide6
            pyside_ver = PySide6.__version__
        except Exception:
            pass
        try:
            import cv2
            cv_ver = cv2.__version__
        except Exception:
            pass
        try:
            import mediapipe as mp
            mp_ver = getattr(mp, "__version__", "0.10.x")
        except Exception:
            pass

        info_rows = [
            ("Version:", VERSION),
            ("Build Number:", BUILD_NUMBER),
            ("Release Channel:", RELEASE_CHANNEL),
            ("Build Date:", BUILD_DATE),
            ("Developer:", DEVELOPER),
            ("Organization:", COMPANY),
            ("License:", LICENSE),
            ("Copyright:", COPYRIGHT),
            ("Python Runtime:", py_ver),
            ("PySide6 / Qt Engine:", pyside_ver),
            ("OpenCV Vision Engine:", cv_ver),
            ("MediaPipe 3D Tracker:", mp_ver),
            ("Operating System:", f"{platform.system()} {platform.release()} ({platform.machine()})"),
            ("Repository URL:", WEBSITE),
        ]

        for k_text, v_text in info_rows:
            row = QHBoxLayout()
            k = QLabel(k_text)
            k.setFixedWidth(180)
            k.setStyleSheet("color: #8f96a3; font-size: 12px; font-weight: 600;")

            v = QLabel(v_text)
            v.setStyleSheet("color: #00e5ff; font-size: 12px; font-weight: 700; font-family: 'Consolas', monospace;")
            v.setTextInteractionFlags(Qt.TextSelectableByMouse)

            row.addWidget(k)
            row.addWidget(v, stretch=1)
            ci_layout.addLayout(row)

        layout.addWidget(card_info)
        layout.addStretch()

