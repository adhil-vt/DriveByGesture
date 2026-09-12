"""
gesturedrive.gui.gesture_widget
===============================
GestureWidget: Displays detected gesture name, confidence progress bar, and mapped action badge.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QProgressBar, QVBoxLayout


class GestureWidget(QFrame):
    """
    Widget displaying active gesture recognition telemetry, visual confidence bar, and mapped action.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("statusCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        # Header Title
        lbl_title = QLabel("GESTURE RECOGNITION")
        lbl_title.setObjectName("telemetryLabel")
        layout.addWidget(lbl_title)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(6)

        # Row 0: Gesture
        lbl_g_title = QLabel("Gesture:")
        lbl_g_title.setFixedWidth(65)
        lbl_g_title.setStyleSheet("color: #8f96a3; font-size: 11px; font-weight: 600;")
        self.val_gesture = QLabel("None")
        self.val_gesture.setStyleSheet("color: #00e676; font-weight: 700; font-size: 15px;")

        # Row 1: Action
        lbl_a_title = QLabel("Action:")
        lbl_a_title.setFixedWidth(65)
        lbl_a_title.setStyleSheet("color: #8f96a3; font-size: 11px; font-weight: 600;")
        self.val_action = QLabel("None")
        self.val_action.setStyleSheet("color: #ffb300; font-weight: 700; font-size: 15px;")

        grid.addWidget(lbl_g_title, 0, 0)
        grid.addWidget(self.val_gesture, 0, 1)
        grid.addWidget(lbl_a_title, 1, 0)
        grid.addWidget(self.val_action, 1, 1)

        layout.addLayout(grid)

        # Confidence Progress Bar
        conf_box = QHBoxLayout()
        conf_box.setSpacing(10)

        lbl_c_title = QLabel("Confidence:")
        lbl_c_title.setStyleSheet("color: #8f96a3; font-size: 11px; font-weight: 600;")

        self.pb_confidence = QProgressBar()
        self.pb_confidence.setObjectName("pbConfidence")
        self.pb_confidence.setRange(0, 100)
        self.pb_confidence.setValue(0)
        self.pb_confidence.setFormat("%v%")

        conf_box.addWidget(lbl_c_title)
        conf_box.addWidget(self.pb_confidence, stretch=1)

        layout.addLayout(conf_box)

    def update_gesture(self, gesture_name: str, confidence: float, action_name: str) -> None:
        """Update gesture name, confidence percent progress bar, and mapped action."""
        g_name = gesture_name if gesture_name and gesture_name != "Unknown" else "None"
        a_name = action_name if action_name else "None"
        conf_pct = int(round(confidence * 100)) if g_name != "None" else 0

        self.val_gesture.setText(g_name)
        self.val_action.setText(a_name)
        self.pb_confidence.setValue(conf_pct)

        if g_name != "None":
            self.val_gesture.setStyleSheet("color: #00e676; font-weight: 700; font-size: 16px;")
        else:
            self.val_gesture.setStyleSheet("color: #8f96a3; font-weight: 700; font-size: 16px;")
