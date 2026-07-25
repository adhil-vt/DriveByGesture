"""
gesturedrive.gui.control_panel
==============================
Bottom control panel widget providing Start, Stop, Calibrate, Settings, and Exit action buttons.
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
    exit_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("controlPanel")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 12, 20, 12)
        layout.setSpacing(14)

        # 1. Start Button
        self.btn_start = QPushButton("▶  Start Pipeline")
        self.btn_start.setObjectName("btnStart")

        # 2. Stop Button
        self.btn_stop = QPushButton("⏹  Stop Pipeline")
        self.btn_stop.setObjectName("btnStop")
        self.btn_stop.setEnabled(False)

        # 3. Calibrate Button ("Coming Soon" for Phase 9.2)
        self.btn_calibrate = QPushButton("🎯  Calibrate")
        self.btn_calibrate.setObjectName("btnCalibrate")

        # 4. Settings Button ("Coming Soon" for Phase 9.2)
        self.btn_settings = QPushButton("⚙  Settings")
        self.btn_settings.setObjectName("btnSettings")

        # 5. Exit Button
        self.btn_exit = QPushButton("✕  Exit")
        self.btn_exit.setObjectName("btnExit")

        layout.addWidget(self.btn_start)
        layout.addWidget(self.btn_stop)
        layout.addSpacing(10)
        layout.addWidget(self.btn_calibrate)
        layout.addWidget(self.btn_settings)
        layout.addStretch()
        layout.addWidget(self.btn_exit)

        # Connections
        self.btn_start.clicked.connect(self._on_start_clicked)
        self.btn_stop.clicked.connect(self._on_stop_clicked)
        self.btn_calibrate.clicked.connect(self._on_calibrate_clicked)
        self.btn_settings.clicked.connect(self._on_settings_clicked)
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
        QMessageBox.information(
            self,
            "Calibrate",
            "Full Calibration Wizard GUI is coming soon in Phase 9.2!\n\n"
            "Keyboard shortcut [C] in preview demo is supported by backend.",
        )

    def _on_settings_clicked(self) -> None:
        QMessageBox.information(
            self,
            "Settings",
            "Application Settings & Profile Manager GUI coming soon in Phase 9.2!",
        )
