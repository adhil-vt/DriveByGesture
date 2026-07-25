"""
gesturedrive.gui.camera_widget
==============================
Camera preview widget rendering real-time BGR video frames in PySide6.
"""

from __future__ import annotations

import cv2
import numpy as np
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout


class CameraWidget(QFrame):
    """
    Widget rendering the live camera preview feed with automatic aspect-ratio scaling.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("cameraCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Image display label
        self.lbl_image = QLabel()
        self.lbl_image.setAlignment(Qt.AlignCenter)
        self.lbl_image.setMinimumSize(640, 480)
        self.lbl_image.setStyleSheet("background-color: #0b0b10; border-radius: 8px;")

        layout.addWidget(self.lbl_image)

        self._last_frame: np.ndarray | None = None
        self.show_offline_banner("Camera Offline")

    def update_frame(self, frame_bgr: np.ndarray) -> None:
        """
        Update the preview label with a new OpenCV BGR image frame.
        """
        self._last_frame = frame_bgr
        h, w, ch = frame_bgr.shape
        bytes_per_line = ch * w

        # Convert BGR to RGB for PySide6
        rgb_frame = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        q_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)

        # Scale image keeping aspect ratio
        target_size = self.lbl_image.size()
        scaled_pixmap = QPixmap.fromImage(q_img).scaled(
            target_size, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.lbl_image.setPixmap(scaled_pixmap)

    def show_offline_banner(self, message: str = "Camera Offline") -> None:
        """Display placeholder card when camera is offline or stopped."""
        self._last_frame = None
        pixmap = QPixmap(640, 480)
        pixmap.fill(Qt.GlobalColor.transparent)

        self.lbl_image.setText(
            f"📷  {message}\n\nPress [START] to launch live gesture pipeline."
        )
        self.lbl_image.setStyleSheet(
            "background-color: #0b0b10; color: #6c6c84; font-size: 16px; "
            "font-weight: bold; border-radius: 8px; text-align: center;"
        )

    def show_error_banner(self, error_msg: str = "Camera Not Available") -> None:
        """Display error banner when camera capture fails."""
        self._last_frame = None
        self.lbl_image.setText(f"⚠️  {error_msg}\n\nPlease check camera connection.")
        self.lbl_image.setStyleSheet(
            "background-color: #1a0b0e; color: #ff1744; font-size: 16px; "
            "font-weight: bold; border-radius: 8px; text-align: center;"
        )

    def resizeEvent(self, event) -> None:
        """Re-render current frame on widget resize."""
        super().resizeEvent(event)
        if self._last_frame is not None:
            self.update_frame(self._last_frame)
