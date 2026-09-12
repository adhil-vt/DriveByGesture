"""
gesturedrive.gui.camera_widget
==============================
Camera preview widget rendering real-time BGR video frames in PySide6 with semi-transparent HUD overlay.
"""

from __future__ import annotations

import cv2
import numpy as np
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout


class CameraWidget(QFrame):
    """
    Widget rendering the live camera preview feed with automatic aspect-ratio scaling and modern HUD overlay.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("cameraCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        # Image display label
        self.lbl_image = QLabel()
        self.lbl_image.setAlignment(Qt.AlignCenter)
        self.lbl_image.setMinimumSize(640, 480)
        self.lbl_image.setStyleSheet("background-color: #0d0e12; border-radius: 10px;")

        layout.addWidget(self.lbl_image)

        self._last_frame: np.ndarray | None = None
        self.mirror_preview: bool = True
        self.overlay_enabled: bool = True
        self.show_offline_banner("Camera Offline")

    def update_frame(self, frame_bgr: np.ndarray, overlay_info: dict | None = None) -> None:
        """
        Update preview label with new OpenCV BGR frame and optional HUD overlay.
        """
        display_frame = frame_bgr.copy()
        self._last_frame = frame_bgr

        # Apply visual display mirror flip to camera frame first if enabled
        if self.mirror_preview:
            display_frame = cv2.flip(display_frame, 1)

        # Render HUD telemetry overlay AFTER mirroring so text remains unmirrored and fully readable
        if self.overlay_enabled and overlay_info:
            self._render_hud_overlay(display_frame, overlay_info)

        h, w, ch = display_frame.shape
        bytes_per_line = ch * w

        # Convert BGR to RGB for PySide6
        rgb_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
        q_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)

        # Scale image keeping aspect ratio
        target_size = self.lbl_image.size()
        scaled_pixmap = QPixmap.fromImage(q_img).scaled(
            target_size, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.lbl_image.setPixmap(scaled_pixmap)

    def _render_hud_overlay(self, image: np.ndarray, info: dict) -> None:
        """Render modern OpenCV HUD badge overlay onto frame."""
        fps = info.get("processing_fps", info.get("fps", 0.0))
        e2e_ms = info.get("end_to_end_latency_ms", info.get("latency_ms", 0.0))
        gesture = info.get("gesture", "None")
        g_conf = info.get("gesture_confidence", 0.0)
        angle = info.get("steering_angle", 0.0)
        t_conf = info.get("tracking_confidence", 0.0)

        h, w = image.shape[:2]
        font = cv2.FONT_HERSHEY_SIMPLEX

        # HUD Card top-left
        card_w, card_h = 230, 96
        card_x, card_y = 16, 16

        # Check bounds
        if card_y + card_h < h and card_x + card_w < w:
            sub = image[card_y : card_y + card_h, card_x : card_x + card_w]
            black_bg = np.full_like(sub, (13, 14, 18))
            cv2.addWeighted(sub, 0.2, black_bg, 0.8, 0, sub)
            cv2.rectangle(image, (card_x, card_y), (card_x + card_w, card_y + card_h), (40, 44, 60), 1)
            cv2.line(image, (card_x, card_y), (card_x + card_w, card_y), (255, 229, 0), 2)

            # Text lines
            fps_text = f"FPS: {fps:.1f} ({e2e_ms:.0f}ms)" if e2e_ms > 0 else f"FPS: {fps:.1f}"
            cv2.putText(image, fps_text, (card_x + 12, card_y + 24), font, 0.45, (0, 230, 0), 1, cv2.LINE_AA)

            g_str = f"Gesture: {gesture}" + (f" ({int(g_conf*100)}%)" if gesture != "None" else "")
            cv2.putText(image, g_str, (card_x + 12, card_y + 46), font, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

            g_action = info.get("action", "Idle")
            cv2.putText(image, f"Action: {g_action}", (card_x + 12, card_y + 68), font, 0.45, (255, 229, 0), 1, cv2.LINE_AA)

            t_str = f"Track Conf: {int(t_conf*100)}%" if t_conf > 0.0 else "Track Conf: N/A"
            cv2.putText(image, t_str, (card_x + 12, card_y + 88), font, 0.40, (143, 150, 163), 1, cv2.LINE_AA)

        # Active Interaction Workspace Overlay in Desktop Mode
        if info.get("show_workspace_overlay", True) and str(info.get("mode", "")).lower() == "desktop":
            ws_w = info.get("workspace_w_pct", 0.80)
            ws_h = info.get("workspace_h_pct", 0.80)
            margin_x = (1.0 - max(0.50, min(1.0, ws_w))) / 2.0
            margin_y = (1.0 - max(0.50, min(1.0, ws_h))) / 2.0

            rx1 = int(w * margin_x)
            ry1 = int(h * margin_y)
            rx2 = int(w * (1.0 - margin_x))
            ry2 = int(h * (1.0 - margin_y))

            # Semi-transparent cyan bounding box
            cv2.rectangle(image, (rx1, ry1), (rx2, ry2), (255, 229, 0), 1, cv2.LINE_AA)

            # High-tech corner brackets
            b_len = 16
            cyan = (255, 229, 0)
            thick = 2
            cv2.line(image, (rx1, ry1), (rx1 + b_len, ry1), cyan, thick, cv2.LINE_AA)
            cv2.line(image, (rx1, ry1), (rx1, ry1 + b_len), cyan, thick, cv2.LINE_AA)
            cv2.line(image, (rx2, ry1), (rx2 - b_len, ry1), cyan, thick, cv2.LINE_AA)
            cv2.line(image, (rx2, ry1), (rx2, ry1 + b_len), cyan, thick, cv2.LINE_AA)
            cv2.line(image, (rx1, ry2), (rx1 + b_len, ry2), cyan, thick, cv2.LINE_AA)
            cv2.line(image, (rx1, ry2), (rx1, ry2 - b_len), cyan, thick, cv2.LINE_AA)
            cv2.line(image, (rx2, ry2), (rx2 - b_len, ry2), cyan, thick, cv2.LINE_AA)
            cv2.line(image, (rx2, ry2), (rx2, ry2 - b_len), cyan, thick, cv2.LINE_AA)

            # Workspace text label
            lbl_text = f"ACTIVE WORKSPACE [{int(ws_w*100)}% x {int(ws_h*100)}%]"
            lbl_y = ry1 - 8 if ry1 > 20 else ry1 + 18
            cv2.putText(image, lbl_text, (rx1 + 6, lbl_y), font, 0.40, (255, 229, 0), 1, cv2.LINE_AA)

    def show_offline_banner(self, message: str = "Camera Offline") -> None:
        """Display polished empty state card when camera is offline or stopped."""
        self._last_frame = None
        self.lbl_image.setText(
            f"📷\n\nCamera Offline\n\nPress '▶  Start Pipeline' below to begin real-time gesture tracking."
        )
        self.lbl_image.setStyleSheet(
            "background-color: #121620; color: #8f96a3; font-size: 14px; "
            "font-weight: 600; border: 1px dashed #242a3c; border-radius: 10px; padding: 40px;"
        )

    def show_error_banner(self, error_msg: str = "Camera Not Available") -> None:
        """Display error banner card when camera capture fails."""
        self._last_frame = None
        self.lbl_image.setText(
            f"⚠️\n\nCAMERA CAPTURE ERROR\n\n{error_msg}\n\nPlease check USB camera connection or Settings → Camera device index."
        )
        self.lbl_image.setStyleSheet(
            "background-color: #1c1214; color: #ff5252; font-size: 14px; "
            "font-weight: 600; border: 1px dashed #ff5252; border-radius: 10px; padding: 40px;"
        )

    def resizeEvent(self, event) -> None:
        """Re-render current frame on widget resize."""
        super().resizeEvent(event)
        if self._last_frame is not None:
            self.update_frame(self._last_frame)
