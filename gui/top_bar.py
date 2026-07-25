"""
gesturedrive.gui.top_bar
========================
Top Bar widget displaying application title, live FPS, and system status.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel


class TopBarWidget(QFrame):
    """
    Top application bar containing logo/title, live FPS telemetry, and system status.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("topBar")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 12, 20, 12)

        # Title Label
        self.lbl_title = QLabel("DriveByGesture")
        self.lbl_title.setObjectName("appTitle")

        # Subtitle / Version tag
        self.lbl_subtitle = QLabel("CONTROL CENTER")
        self.lbl_subtitle.setStyleSheet("color: #6c6c84; font-size: 11px; font-weight: bold; margin-left: 8px;")

        title_box = QHBoxLayout()
        title_box.setSpacing(4)
        title_box.addWidget(self.lbl_title)
        title_box.addWidget(self.lbl_subtitle)
        title_box.addStretch()

        # Telemetry: Live FPS
        self.lbl_fps = QLabel("FPS: --")
        self.lbl_fps.setStyleSheet("color: #00e676; font-size: 14px; font-weight: bold; background: #12121a; padding: 6px 14px; border-radius: 6px; border: 1px solid #282838;")

        # Application Status Indicator
        self.lbl_status = QLabel("Status: Ready")
        self.lbl_status.setStyleSheet("color: #00e5ff; font-size: 13px; font-weight: bold; background: #12121a; padding: 6px 14px; border-radius: 6px; border: 1px solid #282838;")

        layout.addLayout(title_box)
        layout.addWidget(self.lbl_fps)
        layout.addSpacing(10)
        layout.addWidget(self.lbl_status)

    def update_fps(self, fps: float) -> None:
        """Update live FPS display."""
        self.lbl_fps.setText(f"FPS: {fps:.1f}")

    def update_status(self, status: str, color_hex: str = "#00e5ff") -> None:
        """Update status display string and accent color."""
        self.lbl_status.setText(f"Status: {status}")
        self.lbl_status.setStyleSheet(
            f"color: {color_hex}; font-size: 13px; font-weight: bold; "
            f"background: #12121a; padding: 6px 14px; border-radius: 6px; border: 1px solid #282838;"
        )
