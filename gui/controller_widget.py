"""
gesturedrive.gui.controller_widget
==================================
ControllerWidget: Displays Virtual Xbox Controller hardware state using visual progress bars for stick X and triggers RT/LT.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QProgressBar, QVBoxLayout


class ControllerWidget(QFrame):
    """
    Widget displaying active virtual controller status, stick position gauge, and trigger progress bars.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("statusCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        # Header Title
        lbl_title = QLabel("VIRTUAL XBOX CONTROLLER")
        lbl_title.setObjectName("telemetryLabel")
        layout.addWidget(lbl_title)

        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(6)

        # Hardware Status | Buttons
        lbl_s_title = QLabel("Status:")
        lbl_s_title.setStyleSheet("color: #8f96a3; font-size: 11px; font-weight: 600;")
        self.val_status = QLabel("Ready")
        self.val_status.setStyleSheet("color: #00e676; font-weight: 700; font-size: 13px;")

        lbl_btn_title = QLabel("Buttons:")
        lbl_btn_title.setStyleSheet("color: #8f96a3; font-size: 11px; font-weight: 600;")
        self.val_buttons = QLabel("None")
        self.val_buttons.setStyleSheet("color: #ffb300; font-weight: 700; font-size: 13px;")

        grid.addWidget(lbl_s_title, 0, 0)
        grid.addWidget(self.val_status, 0, 1)
        grid.addWidget(lbl_btn_title, 0, 2)
        grid.addWidget(self.val_buttons, 0, 3)

        layout.addLayout(grid)

        # Visual Gauges & Progress Bars
        gauges_layout = QVBoxLayout()
        gauges_layout.setSpacing(6)

        # 1. Left Stick X Gauge
        stick_box = QHBoxLayout()
        lbl_lx = QLabel("Stick X:")
        lbl_lx.setStyleSheet("color: #8f96a3; font-size: 11px; font-weight: 600; min-width: 50px;")
        self.pb_stick_x = QProgressBar()
        self.pb_stick_x.setRange(-32768, 32767)
        self.pb_stick_x.setValue(0)
        self.pb_stick_x.setFormat("%v")

        stick_box.addWidget(lbl_lx)
        stick_box.addWidget(self.pb_stick_x, stretch=1)
        gauges_layout.addLayout(stick_box)

        # 2. Accelerator (RT) Progress Bar
        rt_box = QHBoxLayout()
        lbl_rt = QLabel("Accel (RT):")
        lbl_rt.setStyleSheet("color: #8f96a3; font-size: 11px; font-weight: 600; min-width: 50px;")
        self.pb_rt = QProgressBar()
        self.pb_rt.setObjectName("pbTriggerRT")
        self.pb_rt.setRange(0, 255)
        self.pb_rt.setValue(0)
        self.pb_rt.setFormat("%v")

        rt_box.addWidget(lbl_rt)
        rt_box.addWidget(self.pb_rt, stretch=1)
        gauges_layout.addLayout(rt_box)

        # 3. Brake (LT) Progress Bar
        lt_box = QHBoxLayout()
        lbl_lt = QLabel("Brake (LT):")
        lbl_lt.setStyleSheet("color: #8f96a3; font-size: 11px; font-weight: 600; min-width: 50px;")
        self.pb_lt = QProgressBar()
        self.pb_lt.setObjectName("pbTriggerLT")
        self.pb_lt.setRange(0, 255)
        self.pb_lt.setValue(0)
        self.pb_lt.setFormat("%v")

        lt_box.addWidget(lbl_lt)
        lt_box.addWidget(self.pb_lt, stretch=1)
        gauges_layout.addLayout(lt_box)

        layout.addLayout(gauges_layout)

    def update_controller(
        self, status: str, stick_x: int, rt_val: int, lt_val: int, buttons: str
    ) -> None:
        """Update controller telemetry values and visual progress gauges."""
        self.val_status.setText(status or "Ready")
        self.val_buttons.setText(buttons or "None")

        self.pb_stick_x.setValue(int(stick_x))
        self.pb_rt.setValue(int(rt_val))
        self.pb_lt.setValue(int(lt_val))
