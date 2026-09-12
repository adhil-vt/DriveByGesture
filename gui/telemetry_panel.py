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
from gui.game_status_widget import GameStatusWidget
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
        self.setFixedWidth(410)

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

        # 0. Game Status Card (first, most prominent)
        self.game_status = GameStatusWidget()
        layout.addWidget(self.game_status)

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

    def update_game_status(self, game_name: str) -> None:
        """
        Update the game status card.
        Pass empty string or None to show idle state.
        """
        if game_name:
            self.game_status.set_game(game_name)
        else:
            self.game_status.set_idle()

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
        mode = data.get("mode", "driving")
        action_name = data.get("desktop_action", "None") if mode == "desktop" else data.get("action", "None")
        self.gesture_widget.update_gesture(
            gesture_name=data.get("gesture", "None"),
            confidence=data.get("gesture_confidence", 0.0),
            action_name=action_name,
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
