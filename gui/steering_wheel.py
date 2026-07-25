"""
gesturedrive.gui.steering_wheel
===============================
SteeringWheelWidget: Premium vector steering wheel widget drawn via PySide6 QPainter that rotates
in real-time according to the active steering angle.
"""

from __future__ import annotations

import math
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QWidget


class SteeringWheelWidget(QWidget):
    """
    Vector steering wheel rendering component that rotates smoothly to display steering tilt angle.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.steering_angle: float = 0.0
        self.setMinimumSize(240, 240)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)

    def set_angle(self, angle_deg: float) -> None:
        """Update active steering angle in degrees and trigger repaint."""
        self.steering_angle = float(angle_deg)
        self.update()

    def paintEvent(self, event) -> None:
        """Render premium vector steering wheel using QPainter."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        cx = w / 2.0
        cy = h / 2.0
        radius = min(w, h) / 2.0 - 12.0

        if radius <= 15.0:
            return

        # Save painter state and transform origin to center
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(self.steering_angle)

        # 1. Outer Leather Rim Shadow & Body
        rim_width = max(14.0, radius * 0.16)
        rim_rect = QRectF(-radius, -radius, radius * 2.0, radius * 2.0)

        # Outer Rim Shadow
        painter.setPen(QPen(QColor("#08090d"), rim_width + 4.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(rim_rect)

        # Outer Leather Rim
        rim_pen = QPen(QColor("#1c202c"), rim_width)
        rim_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(rim_pen)
        painter.drawEllipse(rim_rect)

        # Inner Rim Glowing Accent Ring
        inner_r = radius - rim_width / 2.0
        inner_rim_rect = QRectF(-inner_r, -inner_r, inner_r * 2.0, inner_r * 2.0)
        painter.setPen(QPen(QColor("#00e5ff"), 2.0))
        painter.drawEllipse(inner_rim_rect)

        # 2. Steering Spokes (3-Spoke Design: Left, Right, Bottom)
        spoke_pen = QPen(QColor("#32384e"), max(8.0, radius * 0.10))
        painter.setPen(spoke_pen)

        inner_hub_r = radius * 0.32
        outer_spoke_r = radius - rim_width / 2.0

        # Spoke 1: Left (150 degrees)
        angle_left = math.radians(150)
        p_left_start = QPointF(inner_hub_r * math.cos(angle_left), inner_hub_r * math.sin(angle_left))
        p_left_end = QPointF(outer_spoke_r * math.cos(angle_left), outer_spoke_r * math.sin(angle_left))
        painter.drawLine(p_left_start, p_left_end)

        # Spoke 2: Right (30 degrees)
        angle_right = math.radians(30)
        p_right_start = QPointF(inner_hub_r * math.cos(angle_right), inner_hub_r * math.sin(angle_right))
        p_right_end = QPointF(outer_spoke_r * math.cos(angle_right), outer_spoke_r * math.sin(angle_right))
        painter.drawLine(p_right_start, p_right_end)

        # Spoke 3: Bottom (90 degrees)
        angle_bottom = math.radians(90)
        p_bottom_start = QPointF(inner_hub_r * math.cos(angle_bottom), inner_hub_r * math.sin(angle_bottom))
        p_bottom_end = QPointF(outer_spoke_r * math.cos(angle_bottom), outer_spoke_r * math.sin(angle_bottom))
        painter.drawLine(p_bottom_start, p_bottom_end)

        # 3. Center Hub Cap
        hub_rect = QRectF(-inner_hub_r, -inner_hub_r, inner_hub_r * 2.0, inner_hub_r * 2.0)
        painter.setPen(QPen(QColor("#00e5ff"), 2.0))
        painter.setBrush(QBrush(QColor("#141620")))
        painter.drawEllipse(hub_rect)

        # Inner Emblem Ring
        emblem_r = inner_hub_r * 0.45
        emblem_rect = QRectF(-emblem_r, -emblem_r, emblem_r * 2.0, emblem_r * 2.0)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor("#00e5ff")))
        painter.drawEllipse(emblem_rect)

        # 4. Top Alignment Marker Pin (Red reference notch)
        notch_w = max(8.0, radius * 0.08)
        notch_h = rim_width + 4.0
        notch_rect = QRectF(-notch_w / 2.0, -radius - 2.0, notch_w, notch_h)
        painter.setBrush(QBrush(QColor("#ff1744")))
        painter.drawRoundedRect(notch_rect, 3.0, 3.0)

        painter.restore()
