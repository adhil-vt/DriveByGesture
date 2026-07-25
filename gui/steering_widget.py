"""
gesturedrive.gui.steering_widget
================================
SteeringWidget & LiveSteeringBar: Steering metrics display and real-time horizontal position bar.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPainter
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget


class LiveSteeringBar(QWidget):
    """
    Horizontal position bar widget visualizing normalized steering position in real time.
    Format: LEFT  <==========|==========>  RIGHT
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.normalized_val: float = 0.0  # Range [-1.0, 1.0]
        self.setMinimumHeight(28)

    def set_value(self, norm_val: float) -> None:
        """Update normalized steering value in range [-1.0, 1.0]."""
        self.normalized_val = max(-1.0, min(1.0, float(norm_val)))
        self.update()

    def paintEvent(self, event) -> None:
        """Draw horizontal bar with center origin pin and directional bar extension."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = float(self.width())
        h = float(self.height())

        # Track background bar
        track_h = 10.0
        track_y = (h - track_h) / 2.0
        track_rect = QRectF(0.0, track_y, w, track_h)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor("#11131a")))
        painter.drawRoundedRect(track_rect, 5.0, 5.0)

        # Center reference point
        cx = w / 2.0

        # Bar extension based on normalized value
        if abs(self.normalized_val) > 0.01:
            bar_w = abs(self.normalized_val) * (w / 2.0)
            if self.normalized_val < 0.0:
                bar_rect = QRectF(cx - bar_w, track_y, bar_w, track_h)
                bar_color = QColor("#ff1744") if self.normalized_val < -0.8 else QColor("#00e5ff")
            else:
                bar_rect = QRectF(cx, track_y, bar_w, track_h)
                bar_color = QColor("#00e676") if self.normalized_val > 0.8 else QColor("#00e5ff")

            painter.setBrush(QBrush(bar_color))
            painter.drawRoundedRect(bar_rect, 4.0, 4.0)

        # Center origin pin
        pin_w = 4.0
        pin_h = track_h + 8.0
        pin_rect = QRectF(cx - pin_w / 2.0, (h - pin_h) / 2.0, pin_w, pin_h)
        painter.setBrush(QBrush(QColor("#ffffff")))
        painter.drawRoundedRect(pin_rect, 2.0, 2.0)


class SteeringWidget(QFrame):
    """
    Widget displaying detailed steering metrics aligned in 2 columns and live position bar.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("statusCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        # Header Title
        lbl_title = QLabel("STEERING METRICS")
        lbl_title.setObjectName("telemetryLabel")
        layout.addWidget(lbl_title)

        # 2-Column Metrics Grid
        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(6)

        # Row 0: Angle | Direction
        lbl_a_title = QLabel("Angle:")
        lbl_a_title.setStyleSheet("color: #8f96a3; font-size: 11px; font-weight: 600;")
        self.val_angle = QLabel("0.0°")
        self.val_angle.setStyleSheet("color: #00e5ff; font-weight: 700; font-size: 15px;")

        lbl_d_title = QLabel("Direction:")
        lbl_d_title.setStyleSheet("color: #8f96a3; font-size: 11px; font-weight: 600;")
        self.val_direction = QLabel("CENTER")
        self.val_direction.setStyleSheet("color: #ffffff; font-weight: 700; font-size: 15px;")

        grid.addWidget(lbl_a_title, 0, 0)
        grid.addWidget(self.val_angle, 0, 1)
        grid.addWidget(lbl_d_title, 0, 2)
        grid.addWidget(self.val_direction, 0, 3)

        # Row 1: Normalized | Raw
        lbl_n_title = QLabel("Normalized:")
        lbl_n_title.setStyleSheet("color: #8f96a3; font-size: 11px; font-weight: 600;")
        self.val_norm = QLabel("0.00")
        self.val_norm.setStyleSheet("color: #00e676; font-weight: 700; font-size: 15px;")

        lbl_r_title = QLabel("Raw Value:")
        lbl_r_title.setStyleSheet("color: #8f96a3; font-size: 11px; font-weight: 600;")
        self.val_raw = QLabel("0.0°")
        self.val_raw.setStyleSheet("color: #8f96a3; font-weight: 700; font-size: 15px;")

        grid.addWidget(lbl_n_title, 1, 0)
        grid.addWidget(self.val_norm, 1, 1)
        grid.addWidget(lbl_r_title, 1, 2)
        grid.addWidget(self.val_raw, 1, 3)

        layout.addLayout(grid)

        # Live Position Bar Header & Bar
        bar_header = QHBoxLayout()
        lbl_l = QLabel("LEFT")
        lbl_l.setStyleSheet("color: #8f96a3; font-size: 10px; font-weight: 700;")
        lbl_r = QLabel("RIGHT")
        lbl_r.setStyleSheet("color: #8f96a3; font-size: 10px; font-weight: 700;")
        bar_header.addWidget(lbl_l)
        bar_header.addStretch()
        bar_header.addWidget(lbl_r)

        layout.addLayout(bar_header)

        self.steering_bar = LiveSteeringBar()
        layout.addWidget(self.steering_bar)

    def update_metrics(
        self, angle_deg: float, direction: str, norm_val: float, raw_angle: float
    ) -> None:
        """Update steering angle, direction, normalized value, raw value, and bar position."""
        self.val_angle.setText(f"{angle_deg:+.1f}°")
        self.val_direction.setText(direction)

        if direction == "LEFT":
            self.val_direction.setStyleSheet("color: #ff1744; font-weight: 700; font-size: 15px;")
        elif direction == "RIGHT":
            self.val_direction.setStyleSheet("color: #00e676; font-weight: 700; font-size: 15px;")
        else:
            self.val_direction.setStyleSheet("color: #ffffff; font-weight: 700; font-size: 15px;")

        self.val_norm.setText(f"{norm_val:+.2f}")
        self.val_raw.setText(f"{raw_angle:+.1f}°")
        self.steering_bar.set_value(norm_val)
