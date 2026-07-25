"""
gesturedrive.gui.status_bar
===========================
Bottom status bar displaying component connection indicators (Camera, MediaPipe, Controller, Calibration).
"""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel


class StatusBarWidget(QFrame):
    """
    Bottom bar widget containing status indicators for all major backend subsystems.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("statusBar")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(20)

        # 1. Camera Status
        self.ind_camera = self._create_indicator("Camera", "Stopped", "#6c6c84")
        # 2. MediaPipe Tracking Status
        self.ind_mediapipe = self._create_indicator("MediaPipe", "Idle", "#6c6c84")
        # 3. Virtual Controller Status
        self.ind_controller = self._create_indicator("Virtual Controller", "Disconnected", "#6c6c84")
        # 4. Calibration Status
        self.ind_calibration = self._create_indicator("Calibration", "Default", "#ffb300")

        layout.addWidget(self.ind_camera)
        layout.addWidget(self.ind_mediapipe)
        layout.addWidget(self.ind_controller)
        layout.addWidget(self.ind_calibration)
        layout.addStretch()

    def _create_indicator(self, name: str, initial_status: str, color_hex: str) -> QLabel:
        lbl = QLabel(f"● {name}: {initial_status}")
        lbl.setObjectName("statusIndicator")
        lbl.setStyleSheet(f"color: {color_hex}; font-size: 12px; font-weight: bold;")
        return lbl

    def set_component_status(self, component: str, status_str: str, state: str = "normal") -> None:
        """
        Update status string and indicator color for a component.

        State: "good" (#00e676 green), "warn" (#ffb300 amber), "bad" (#ff1744 red), "neutral" (#6c6c84 gray)
        """
        colors = {
            "good": "#00e676",
            "warn": "#ffb300",
            "bad": "#ff1744",
            "neutral": "#6c6c84",
            "active": "#00e5ff",
        }
        color_hex = colors.get(state, "#6c6c84")

        target_lbl = None
        if component.lower() == "camera":
            target_lbl = self.ind_camera
            name = "Camera"
        elif component.lower() in ("mediapipe", "tracking"):
            target_lbl = self.ind_mediapipe
            name = "MediaPipe"
        elif component.lower() in ("controller", "xbox"):
            target_lbl = self.ind_controller
            name = "Virtual Controller"
        elif component.lower() == "calibration":
            target_lbl = self.ind_calibration
            name = "Calibration"

        if target_lbl is not None:
            target_lbl.setText(f"● {name}: {status_str}")
            target_lbl.setStyleSheet(f"color: {color_hex}; font-size: 12px; font-weight: bold;")
