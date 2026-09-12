"""
gesturedrive.gui.control_panel
==============================
Bottom control panel widget providing Start, Stop, Calibrate, Settings, and Exit action buttons with standardized height and styling.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QMessageBox, QPushButton


class ControlPanelWidget(QFrame):
    """
    Control panel containing application execution buttons.
    """

    start_requested = Signal()
    stop_requested = Signal()
    calibrate_requested = Signal()
    profiles_requested = Signal()
    settings_requested = Signal()
    diagnostics_requested = Signal()
    exit_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("controlPanel")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(12)

        # 1. Start Button (Primary Teal/Cyan Accent)
        self.btn_start = QPushButton("▶   Start Pipeline")
        self.btn_start.setObjectName("btnStart")

        # 2. Stop Button (Danger Red Accent)
        self.btn_stop = QPushButton("⏹   Stop Pipeline")
        self.btn_stop.setObjectName("btnStop")
        self.btn_stop.setEnabled(False)

        # 3. Calibrate Button
        self.btn_calibrate = QPushButton("🎯   Calibrate")
        self.btn_calibrate.setObjectName("btnCalibrate")

        # 4. Profiles Button
        self.btn_profiles = QPushButton("👤   Profiles")
        self.btn_profiles.setObjectName("btnProfiles")

        # 5. Settings Button
        self.btn_settings = QPushButton("⚙   Settings")
        self.btn_settings.setObjectName("btnSettings")

        # 6. Diagnostics Button
        self.btn_diagnostics = QPushButton("🔬   Diagnostics")
        self.btn_diagnostics.setObjectName("btnDiagnostics")

        # 7. Exit Button
        self.btn_exit = QPushButton("✕   Exit")
        self.btn_exit.setObjectName("btnExit")

        layout.addWidget(self.btn_start)
        layout.addWidget(self.btn_stop)
        layout.addSpacing(12)
        layout.addWidget(self.btn_calibrate)
        layout.addWidget(self.btn_profiles)
        layout.addWidget(self.btn_settings)
        layout.addWidget(self.btn_diagnostics)
        layout.addStretch()
        layout.addWidget(self.btn_exit)

        # Connections
        self.btn_start.clicked.connect(self._on_start_clicked)
        self.btn_stop.clicked.connect(self._on_stop_clicked)
        self.btn_calibrate.clicked.connect(self._on_calibrate_clicked)
        self.btn_profiles.clicked.connect(self._on_profiles_clicked)
        self.btn_settings.clicked.connect(self._on_settings_clicked)
        self.btn_diagnostics.clicked.connect(self._on_diagnostics_clicked)
        self.btn_exit.clicked.connect(self._on_exit_clicked)

    def set_pipeline_running(self, running: bool) -> None:
        """Update button enabled states based on running state."""
        self.btn_start.setEnabled(not running)
        self.btn_stop.setEnabled(running)

    def _on_start_clicked(self) -> None:
        self.start_requested.emit()

    def _on_stop_clicked(self) -> None:
        self.stop_requested.emit()

    def _on_exit_clicked(self) -> None:
        self.exit_requested.emit()

    def _on_calibrate_clicked(self) -> None:
        self.calibrate_requested.emit()

    def _on_profiles_clicked(self) -> None:
        self.profiles_requested.emit()

    def _on_settings_clicked(self) -> None:
        self.settings_requested.emit()

    def _on_diagnostics_clicked(self) -> None:
        self.diagnostics_requested.emit()
