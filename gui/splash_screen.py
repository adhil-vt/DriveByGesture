"""
gesturedrive.gui.splash_screen
================================
DriveByGestureSplashScreen: Startup splash screen window with prominent application icon,
real-time loading progress, minimum 2.0s display duration, and smooth fade-out transition.
"""

from __future__ import annotations

import time
from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QProgressBar,
    QSplashScreen,
    QVBoxLayout,
    QWidget,
)

from core.resources import get_app_icon
from core.version import APP_NAME, BUILD_NUMBER, RELEASE_CHANNEL, VERSION


class DriveByGestureSplashScreen(QSplashScreen):
    """
    Professional startup splash screen displaying centered prominent application icon,
    branding, version, real-time loading status, and smooth 250ms fade transition.
    """

    def __init__(self) -> None:
        self._start_time = time.time()

        container = QWidget()
        container.resize(560, 360)
        container.setStyleSheet(
            "QWidget { background-color: #0b0e14; color: #ffffff; border: 1px solid #00e5ff; border-radius: 14px; }"
        )

        layout = QVBoxLayout(container)
        layout.setContentsMargins(36, 28, 36, 28)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 1. Large Centered Prominent Application Icon (96x96)
        self.lbl_icon = QLabel()
        self.lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_icon.setPixmap(get_app_icon().pixmap(96, 96))
        self.lbl_icon.setStyleSheet("border: none; margin-bottom: 2px;")
        layout.addWidget(self.lbl_icon)

        # 2. Application Title
        lbl_title = QLabel(APP_NAME)
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_title.setStyleSheet(
            "font-size: 28px; font-weight: 800; color: #00e5ff; border: none; letter-spacing: 1.5px;"
        )
        layout.addWidget(lbl_title)

        # 3. Version & Build Badge
        lbl_version = QLabel(f"v{VERSION}  {RELEASE_CHANNEL}  ({BUILD_NUMBER})")
        lbl_version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_version.setStyleSheet(
            "font-size: 12px; font-weight: 700; color: #ffb300; border: none;"
        )
        layout.addWidget(lbl_version)

        # 4. Tagline
        lbl_subtitle = QLabel("Gesture-Based Driving & Desktop Control")
        lbl_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_subtitle.setStyleSheet(
            "font-size: 12px; font-weight: 600; color: #5b616e; border: none; margin-bottom: 6px;"
        )
        layout.addWidget(lbl_subtitle)

        # 5. Loading Status Message
        self.lbl_status = QLabel("Loading Configuration...")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setStyleSheet(
            "font-size: 12px; font-weight: 600; color: #8f96a3; border: none;"
        )
        layout.addWidget(self.lbl_status)

        # 6. Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(10)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(
            "QProgressBar { background-color: #121620; border: 1px solid #242a3c; border-radius: 6px; height: 10px; }"
            "QProgressBar::chunk { background-color: #00e5ff; border-radius: 5px; }"
        )
        layout.addWidget(self.progress_bar)

        pixmap = container.grab()
        super().__init__(pixmap, Qt.WindowStaysOnTopHint)

        self._container = container
        self._fade_anim = None

    def set_progress(self, percent: int, message: str) -> None:
        """Update splash screen progress bar percentage and status message."""
        self.progress_bar.setValue(percent)
        self.lbl_status.setText(message)

        pix = self._container.grab()
        self.setPixmap(pix)
        QApplication.processEvents()

    def finish_and_transition(self, main_window: QWidget, min_display_sec: float = 5.0) -> None:
        """
        Enforce minimum display duration, then smoothly fade out and show main window.
        """
        elapsed = time.time() - self._start_time
        remaining = min_display_sec - elapsed

        # If initialization completes faster than min_display_sec, keep splash visible until 2.0s elapses
        if remaining > 0:
            target_time = time.time() + remaining
            while time.time() < target_time:
                QApplication.processEvents()
                time.sleep(0.01)

        # Update status to Ready
        self.set_progress(100, "Ready.")

        # Smooth 250ms Fade-Out Animation
        self._fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self._fade_anim.setDuration(250)
        self._fade_anim.setStartValue(1.0)
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.setEasingCurve(QEasingCurve.OutCubic)

        def _on_fade_finished():
            main_window.show()
            self.finish(main_window)

        self._fade_anim.finished.connect(_on_fade_finished)
        self._fade_anim.start()

        while self._fade_anim and self._fade_anim.state() == QPropertyAnimation.Running:
            QApplication.processEvents()
            time.sleep(0.01)
