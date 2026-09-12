"""
gesturedrive.gui.top_bar
========================
Top Bar widget displaying application title, live FPS, pipeline status, active profile, and camera name.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton

from gui.mode_widget import ModeSelectorWidget
from gui.profile_widget import ProfileSelectorWidget


class TopBarWidget(QFrame):
    """
    Header bar containing logo/title and modern pill-shaped metadata badges.

    Signals
    -------
    profile_switch_requested(str)
        Re-emitted from ProfileSelectorWidget.
    help_requested()
        Emitted when the Help button is clicked.
    """

    profile_switch_requested = Signal(str)
    mode_switch_requested = Signal(str)
    help_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("topBar")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # Title Box
        self.lbl_title = QLabel("DriveByGesture")
        self.lbl_title.setObjectName("appTitle")

        self.lbl_subtitle = QLabel("CONTROL CENTER")
        self.lbl_subtitle.setStyleSheet(
            "color: #5b616e; font-size: 11px; font-weight: 700; margin-left: 6px; letter-spacing: 1px;"
        )

        title_box = QHBoxLayout()
        title_box.setSpacing(2)
        title_box.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        title_box.addWidget(self.lbl_title)
        title_box.addWidget(self.lbl_subtitle)
        title_box.addStretch()

        # Pill Badges
        self.lbl_fps = QLabel("FPS: --")
        self.lbl_fps.setObjectName("pillBadge")
        self.lbl_fps.setToolTip("Live frames per second processed by background tracking engine")
        self.lbl_fps.setStyleSheet(
            "background-color: #0b0e14; color: #00e676; font-size: 12px; font-weight: 700; "
            "padding: 5px 12px; border-radius: 14px; border: 1px solid #242a3c;"
        )

        self.lbl_status = QLabel("Pipeline: Stopped")
        self.lbl_status.setObjectName("pillBadge")
        self.lbl_status.setToolTip("Current execution status of camera capture and gesture pipeline")
        self.lbl_status.setStyleSheet(
            "background-color: #0b0e14; color: #8f96a3; font-size: 12px; font-weight: 700; "
            "padding: 5px 12px; border-radius: 14px; border: 1px solid #242a3c;"
        )

        self.lbl_camera = QLabel("Camera: Webcam 0")
        self.lbl_camera.setObjectName("pillBadge")
        self.lbl_camera.setToolTip("Currently selected camera capture input device")
        self.lbl_camera.setStyleSheet(
            "background-color: #0b0e14; color: #8f96a3; font-size: 12px; font-weight: 600; "
            "padding: 5px 12px; border-radius: 14px; border: 1px solid #242a3c;"
        )

        # Help Button
        self.btn_help = QPushButton("❓ Help")
        self.btn_help.setToolTip("Open Help & Documentation Center (F1)")
        self.btn_help.setStyleSheet(
            "QPushButton { background-color: #0b0e14; color: #00e5ff; font-size: 12px; font-weight: 700; "
            "padding: 5px 12px; border-radius: 14px; border: 1px solid #242a3c; height: 28px; min-height: 28px; }"
            "QPushButton:hover { background-color: #1a1f2c; color: #ffffff; border-color: #00e5ff; }"
        )
        self.btn_help.clicked.connect(self.help_requested.emit)

        # Interactive profile selector & mode selector
        self.mode_selector = ModeSelectorWidget()
        self.mode_selector.setToolTip("Switch operating mode between Driving (Game Controller) and Desktop (Mouse/Shortcuts)")
        self.mode_selector.mode_switch_requested.connect(self.mode_switch_requested)

        self.profile_selector = ProfileSelectorWidget()
        self.profile_selector.setToolTip("Quickly switch active configuration profile")
        self.profile_selector.profile_switch_requested.connect(self.profile_switch_requested)

        layout.addLayout(title_box)
        layout.addWidget(self.lbl_fps)
        layout.addWidget(self.lbl_status)
        layout.addWidget(self.mode_selector)
        layout.addWidget(self.profile_selector)
        layout.addWidget(self.lbl_camera)
        layout.addWidget(self.btn_help)

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
        """Update active profile name in selector and camera device name."""
        if profile_name:
            self.profile_selector.set_active_profile(profile_name)
        if camera_name:
            self.lbl_camera.setText(f"Camera: {camera_name}")

    def update_mode(self, mode_str: str) -> None:
        """Update active mode in selector."""
        self.mode_selector.set_active_mode(mode_str)
