"""
gesturedrive.gui.top_bar
========================
Top Bar widget displaying application title, live FPS, pipeline status, active profile, and camera name.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel


class TopBarWidget(QFrame):
    """
    Header bar containing logo/title and modern pill-shaped metadata badges.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("topBar")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(10)

        # Title Box
        self.lbl_title = QLabel("DriveByGesture")
        self.lbl_title.setObjectName("appTitle")

        self.lbl_subtitle = QLabel("CONTROL CENTER")
        self.lbl_subtitle.setStyleSheet(
            "color: #5b616e; font-size: 11px; font-weight: 700; margin-left: 6px; letter-spacing: 1px;"
        )

        title_box = QHBoxLayout()
        title_box.setSpacing(2)
        title_box.addWidget(self.lbl_title)
        title_box.addWidget(self.lbl_subtitle)
        title_box.addStretch()

        # Pill Badges
        self.lbl_fps = QLabel("FPS: --")
        self.lbl_fps.setObjectName("pillBadge")
        self.lbl_fps.setStyleSheet(
            "background-color: #11131a; color: #00e676; font-size: 12px; font-weight: 700; "
            "padding: 6px 14px; border-radius: 14px; border: 1px solid #282c3c;"
        )

        self.lbl_status = QLabel("Pipeline: Stopped")
        self.lbl_status.setObjectName("pillBadge")
        self.lbl_status.setStyleSheet(
            "background-color: #11131a; color: #8f96a3; font-size: 12px; font-weight: 700; "
            "padding: 6px 14px; border-radius: 14px; border: 1px solid #282c3c;"
        )

        self.lbl_profile = QLabel("Profile: Default")
        self.lbl_profile.setObjectName("pillBadge")
        self.lbl_profile.setStyleSheet(
            "background-color: #11131a; color: #ffb300; font-size: 12px; font-weight: 700; "
            "padding: 6px 14px; border-radius: 14px; border: 1px solid #282c3c;"
        )

        self.lbl_camera = QLabel("Camera: Integrated Webcam")
        self.lbl_camera.setObjectName("pillBadge")
        self.lbl_camera.setStyleSheet(
            "background-color: #11131a; color: #8f96a3; font-size: 12px; font-weight: 600; "
            "padding: 6px 14px; border-radius: 14px; border: 1px solid #282c3c;"
        )

        layout.addLayout(title_box)
        layout.addWidget(self.lbl_fps)
        layout.addWidget(self.lbl_status)
        layout.addWidget(self.lbl_profile)
        layout.addWidget(self.lbl_camera)

    def update_fps(self, fps: float) -> None:
        """Update live FPS display."""
        self.lbl_fps.setText(f"FPS: {fps:.1f}")

    def update_status(self, status: str, color_hex: str = "#00e5ff") -> None:
        """Update status display string and accent color."""
        self.lbl_status.setText(f"Pipeline: {status}")
        self.lbl_status.setStyleSheet(
            f"background-color: #11131a; color: {color_hex}; font-size: 12px; font-weight: 700; "
            f"padding: 6px 14px; border-radius: 14px; border: 1px solid #282c3c;"
        )

    def update_info(self, profile_name: str | None = None, camera_name: str | None = None) -> None:
        """Update active profile name and camera device name."""
        if profile_name:
            self.lbl_profile.setText(f"Profile: {profile_name}")
        if camera_name:
            self.lbl_camera.setText(f"Camera: {camera_name}")
