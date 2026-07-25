"""
gesturedrive.gui.telemetry_panel
================================
Right dashboard telemetry panel for displaying steering wheel metrics, gesture status, and action state.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QVBoxLayout


class TelemetryPanel(QFrame):
    """
    Right panel dashboard containing status cards for steering telemetry, recognized gestures,
    abstract action states, and controller hardware output status.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("telemetryCard")
        self.setMinimumWidth(320)
        self.setMaximumWidth(400)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header Title
        lbl_header = QLabel("PIPELINE TELEMETRY")
        lbl_header.setObjectName("sectionTitle")
        layout.addWidget(lbl_header)

        # Grid container for cards
        grid = QGridLayout()
        grid.setSpacing(10)

        # Card 1: Steering Angle
        card_steering = self._create_card("STEERING ANGLE", "0.0°", "#00e5ff")
        self.val_steering = card_steering.findChild(QLabel, "telemetryValue")

        # Card 2: Detected Gesture
        card_gesture = self._create_card("DETECTED GESTURE", "None", "#00e676")
        self.val_gesture = card_gesture.findChild(QLabel, "telemetryValue")

        # Card 3: Current Action
        card_action = self._create_card("CURRENT ACTION", "Idle", "#ffb300")
        self.val_action = card_action.findChild(QLabel, "telemetryValue")

        # Card 4: Controller Hardware Status
        card_controller = self._create_card("CONTROLLER STATUS", "Disconnected", "#a0a0b8")
        self.val_controller = card_controller.findChild(QLabel, "telemetryValue")

        layout.addWidget(card_steering)
        layout.addWidget(card_gesture)
        layout.addWidget(card_action)
        layout.addWidget(card_controller)

        # Placeholder Graphic Area for Steering Wheel Visualization (Phase 9.2+)
        self.wheel_placeholder = QFrame()
        self.wheel_placeholder.setObjectName("statusCard")
        self.wheel_placeholder.setMinimumHeight(140)
        wheel_layout = QVBoxLayout(self.wheel_placeholder)
        wheel_layout.setAlignment(Qt.AlignCenter)
        lbl_wheel = QLabel("☸ Steering Wheel Graphic\n(Phase 9.2 Visualization)")
        lbl_wheel.setAlignment(Qt.AlignCenter)
        lbl_wheel.setStyleSheet("color: #4a4a60; font-size: 12px; font-weight: bold;")
        wheel_layout.addWidget(lbl_wheel)

        layout.addWidget(self.wheel_placeholder)
        layout.addStretch()

    def _create_card(self, title: str, initial_val: str, color_hex: str) -> QFrame:
        card = QFrame()
        card.setObjectName("statusCard")

        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(12, 10, 12, 10)
        c_layout.setSpacing(4)

        lbl_t = QLabel(title)
        lbl_t.setObjectName("telemetryLabel")

        lbl_v = QLabel(initial_val)
        lbl_v.setObjectName("telemetryValue")
        lbl_v.setStyleSheet(f"color: {color_hex}; font-size: 18px; font-weight: bold;")

        c_layout.addWidget(lbl_t)
        c_layout.addWidget(lbl_v)
        return card

    def update_telemetry(self, steering_angle: float, gesture: str, action: str, controller: str) -> None:
        """Update live telemetry card values."""
        self.val_steering.setText(f"{steering_angle:+.1f}°")
        self.val_gesture.setText(gesture or "None")
        self.val_action.setText(action or "Idle")
        self.val_controller.setText(controller or "Ready")
