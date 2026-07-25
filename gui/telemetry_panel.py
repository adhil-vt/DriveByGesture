"""
gesturedrive.gui.telemetry_panel
================================
Right dashboard telemetry panel assembling vector steering wheel, steering metrics, gesture status,
controller hardware output, and performance pipeline statistics.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QScrollArea, QVBoxLayout, QWidget

from gui.controller_widget import ControllerWidget
from gui.gesture_widget import GestureWidget
from gui.stats_widget import PipelineStatsWidget
from gui.steering_wheel import SteeringWheelWidget
from gui.steering_widget import SteeringWidget


class TelemetryPanel(QFrame):
    """
    Right panel dashboard assembling live vector steering wheel, steering metrics, gesture status,
    controller hardware output, and performance pipeline statistics.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("telemetryCard")
        self.setMinimumWidth(380)
        self.setMaximumWidth(440)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(12)

        # Header Title
        lbl_header = QLabel("LIVE TELEMETRY DASHBOARD")
        lbl_header.setObjectName("sectionTitle")
        main_layout.addWidget(lbl_header)

        # Scroll Area for clean responsiveness on lower resolution screens
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # 1. Vector Steering Wheel Widget (Centered, 240x240)
        wheel_box = QFrame()
        wheel_box.setObjectName("statusCard")
        w_layout = QVBoxLayout(wheel_box)
        w_layout.setContentsMargins(12, 14, 12, 14)
        w_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.steering_wheel = SteeringWheelWidget()
        w_layout.addWidget(self.steering_wheel)
        layout.addWidget(wheel_box)

        # 2. Detailed Steering Metrics & Live Position Bar
        self.steering_widget = SteeringWidget()
        layout.addWidget(self.steering_widget)

        # 3. Gesture & Mapped Action Panel
        self.gesture_widget = GestureWidget()
        layout.addWidget(self.gesture_widget)

        # 4. Virtual Controller Panel
        self.controller_widget = ControllerWidget()
        layout.addWidget(self.controller_widget)

        # 5. Pipeline Performance Statistics
        self.stats_widget = PipelineStatsWidget()
        layout.addWidget(self.stats_widget)

        layout.addStretch()
        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def update_telemetry_data(self, data: dict) -> None:
        """
        Update all telemetry widgets from enriched telemetry dictionary payload.
        """
        steering_angle = data.get("steering_angle", 0.0)
        direction = data.get("direction", "CENTER")
        norm_val = data.get("normalized_steering", 0.0)
        raw_val = data.get("raw_steering", 0.0)

        # 1. Update Steering Wheel rotation & Steering metrics
        self.steering_wheel.set_angle(steering_angle)
        self.steering_widget.update_metrics(
            angle_deg=steering_angle,
            direction=direction,
            norm_val=norm_val,
            raw_angle=raw_val,
        )

        # 2. Update Gesture & Action
        self.gesture_widget.update_gesture(
            gesture_name=data.get("gesture", "None"),
            confidence=data.get("gesture_confidence", 0.0),
            action_name=data.get("action", "None"),
        )

        # 3. Update Controller output
        self.controller_widget.update_controller(
            status=data.get("controller_status", "Ready"),
            stick_x=data.get("left_stick_x", 0),
            rt_val=data.get("accelerator_rt", 0),
            lt_val=data.get("brake_lt", 0),
            buttons=data.get("buttons_pressed", "None"),
        )

        # 4. Update Pipeline Performance Stats
        self.stats_widget.update_stats(
            camera_fps=data.get("camera_fps", 0.0),
            proc_fps=data.get("processing_fps", 0.0),
            latency_ms=data.get("latency_ms", 0.0),
            tracking_conf=data.get("tracking_confidence", 0.0),
        )

    def update_telemetry(self, steering_angle: float, gesture: str, action: str, controller: str) -> None:
        """Backward compatibility update helper."""
        self.update_telemetry_data({
            "steering_angle": steering_angle,
            "gesture": gesture,
            "action": action,
            "controller_status": controller,
        })
