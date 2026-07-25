"""
gesturedrive.gui.settings_pages
==============================
Modular page widgets for SettingsDialog categories:
General, Camera, Steering, Controller, Calibration, Profiles, and About.
"""

from __future__ import annotations

import os
import sys
import cv2
import numpy as np
import PySide6
import mediapipe as mp
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from calibration.calibration_manager import CalibrationManager
from config.schema import CameraConfig, ControllerConfig, GestureConfig
from gui.steering_widget import LiveSteeringBar


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

        self.lbl_config_path = QLabel("profiles/default_calibration.json")
        self.lbl_config_path.setStyleSheet("color: #8f96a3;")

        self.lbl_profile = QLabel("Default")
        self.lbl_profile.setStyleSheet("color: #ffb300; font-weight: 700;")

        self.cb_auto_save = QCheckBox("Auto-save calibration changes")
        self.cb_auto_save.setChecked(True)

        self.cb_auto_start = QCheckBox("Start pipeline automatically on application launch")
        self.cb_auto_start.setChecked(False)

        self.cb_min_tray = QCheckBox("Minimize to system tray on close (Future)")
        self.cb_min_tray.setChecked(False)
        self.cb_min_tray.setEnabled(False)

        c_layout.addRow("Application Version:", self.lbl_version)
        c_layout.addRow("Configuration File:", self.lbl_config_path)
        c_layout.addRow("Active Profile:", self.lbl_profile)
        c_layout.addRow(self.cb_auto_save)
        c_layout.addRow(self.cb_auto_start)
        c_layout.addRow(self.cb_min_tray)

        layout.addWidget(card)
        layout.addStretch()


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

        self.combo_device = QComboBox()
        self.combo_device.addItems(["0: Integrated Webcam", "1: External Camera", "2: Secondary Camera"])

        self.combo_resolution = QComboBox()
        self.combo_resolution.addItems(["640 x 480 (Recommended)", "1280 x 720 (HD)", "1920 x 1080 (FHD)"])

        self.sb_fps = QSpinBox()
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
        )

    def is_mirror_preview_enabled(self) -> bool:
        return self.cb_mirror.isChecked()

    def is_show_overlay_enabled(self) -> bool:
        return self.cb_overlay.isChecked()


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
        self.dsp_sensitivity = QDoubleSpinBox()
        self.dsp_sensitivity.setRange(0.5, 3.0)
        self.dsp_sensitivity.setSingleStep(0.1)
        self.dsp_sensitivity.setValue(1.0)

        # 2. Deadzone
        self.dsp_deadzone = QDoubleSpinBox()
        self.dsp_deadzone.setRange(0.0, 0.3)
        self.dsp_deadzone.setSingleStep(0.01)
        self.dsp_deadzone.setValue(0.05)

        # 3. Max Steering Angle
        self.sb_max_angle = QSpinBox()
        self.sb_max_angle.setRange(15, 90)
        self.sb_max_angle.setValue(30)
        self.sb_max_angle.setSuffix("°")

        # 4. Smoothing Alpha
        self.dsp_smoothing = QDoubleSpinBox()
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
        return GestureConfig(
            max_steering_angle=float(self.sb_max_angle.value()),
            steering_deadzone=float(self.dsp_deadzone.value()),
            steering_sensitivity=float(self.dsp_sensitivity.value()),
            steering_smoothing_alpha=float(self.dsp_smoothing.value()),
        )


class ControllerPage(QWidget):
    """Virtual Xbox Controller hardware output settings page."""

    reconnect_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

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

        self.combo_type = QComboBox()
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

        self.lbl_cal_file = QLabel("profiles/default_calibration.json")
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
            self, "Export Calibration JSON", "profiles/exported_calibration.json", "JSON Files (*.json)"
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
            self, "Import Calibration JSON", "profiles/", "JSON Files (*.json)"
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
    """Driving Profile Management page."""

    profile_switched = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        lbl_title = QLabel("DRIVING PROFILE MANAGER")
        lbl_title.setObjectName("sectionTitle")
        layout.addWidget(lbl_title)

        card = QFrame()
        card.setObjectName("statusCard")
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(16, 16, 16, 16)
        c_layout.setSpacing(10)

        lbl_active = QLabel("Active Profile: Default")
        lbl_active.setStyleSheet("color: #00e5ff; font-weight: 700; font-size: 15px;")
        c_layout.addWidget(lbl_active)

        self.list_profiles = QListWidget()
        self.list_profiles.addItems(["Default", "SimRacing GT3", "Drift Setup", "Arcade Steering"])
        self.list_profiles.setCurrentRow(0)
        c_layout.addWidget(self.list_profiles)

        btn_box = QHBoxLayout()
        btn_box.setSpacing(10)

        self.btn_create = QPushButton("➕   Create Profile")
        self.btn_create.clicked.connect(self._on_create)

        self.btn_switch = QPushButton("✔   Switch Profile")
        self.btn_switch.setObjectName("btnStart")
        self.btn_switch.clicked.connect(self._on_switch)

        btn_box.addWidget(self.btn_create)
        btn_box.addWidget(self.btn_switch)
        c_layout.addLayout(btn_box)

        layout.addWidget(card)
        layout.addStretch()

    def _on_create(self) -> None:
        QMessageBox.information(self, "Create Profile", "Profile creation will save to profiles/ folder in future release!")

    def _on_switch(self) -> None:
        item = self.list_profiles.currentItem()
        if item:
            name = item.text()
            self.profile_switched.emit(name)
            QMessageBox.information(self, "Profile Switched", f"Active profile set to: {name}")


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

        layout.addWidget(card)
        layout.addStretch()
