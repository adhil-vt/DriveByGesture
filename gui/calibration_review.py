"""
gesturedrive.gui.calibration_review
===================================
ReviewWidget: Review screen widget displaying calculated calibration parameters and normalized preview gauge.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from calibration.calibration_data import CalibrationData
from gui.steering_widget import LiveSteeringBar


class ReviewWidget(QFrame):
    """
    Review summary card displaying captured calibration limits, center angle, range, and live test gauge.
    """

    save_requested = Signal()
    recalibrate_requested = Signal()
    cancel_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("statusCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        # Header Title
        lbl_title = QLabel("CALIBRATION SUMMARY & REVIEW")
        lbl_title.setObjectName("sectionTitle")
        layout.addWidget(lbl_title)

        # Metrics Grid
        grid = QGridLayout()
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(8)

        # Center Angle
        lbl_c_title = QLabel("Center Angle:")
        lbl_c_title.setStyleSheet("color: #8f96a3; font-size: 12px; font-weight: 600;")
        self.val_center = QLabel("0.0°")
        self.val_center.setStyleSheet("color: #00e5ff; font-weight: 700; font-size: 16px;")

        # Left Limit
        lbl_l_title = QLabel("Left Limit:")
        lbl_l_title.setStyleSheet("color: #8f96a3; font-size: 12px; font-weight: 600;")
        self.val_left = QLabel("0.0°")
        self.val_left.setStyleSheet("color: #ff1744; font-weight: 700; font-size: 16px;")

        # Right Limit
        lbl_r_title = QLabel("Right Limit:")
        lbl_r_title.setStyleSheet("color: #8f96a3; font-size: 12px; font-weight: 600;")
        self.val_right = QLabel("0.0°")
        self.val_right.setStyleSheet("color: #00e676; font-weight: 700; font-size: 16px;")

        # Steering Range
        lbl_range_title = QLabel("Steering Range:")
        lbl_range_title.setStyleSheet("color: #8f96a3; font-size: 12px; font-weight: 600;")
        self.val_range = QLabel("0.0°")
        self.val_range.setStyleSheet("color: #ffb300; font-weight: 700; font-size: 16px;")

        # Minimum Threshold
        lbl_thresh_title = QLabel("Minimum Threshold:")
        lbl_thresh_title.setStyleSheet("color: #8f96a3; font-size: 12px; font-weight: 600;")
        self.val_thresh = QLabel("8.0°")
        self.val_thresh.setStyleSheet("color: #8f96a3; font-weight: 700; font-size: 16px;")

        grid.addWidget(lbl_c_title, 0, 0)
        grid.addWidget(self.val_center, 0, 1)
        grid.addWidget(lbl_l_title, 0, 2)
        grid.addWidget(self.val_left, 0, 3)

        grid.addWidget(lbl_r_title, 1, 0)
        grid.addWidget(self.val_right, 1, 1)
        grid.addWidget(lbl_range_title, 1, 2)
        grid.addWidget(self.val_range, 1, 3)

        grid.addWidget(lbl_thresh_title, 2, 0)
        grid.addWidget(self.val_thresh, 2, 1)

        layout.addLayout(grid)

        # Test Steering Position Gauge
        lbl_gauge_title = QLabel("LIVE STEERING RESPONSE PREVIEW:")
        lbl_gauge_title.setStyleSheet("color: #8f96a3; font-size: 11px; font-weight: 600;")
        layout.addWidget(lbl_gauge_title)

        self.preview_bar = LiveSteeringBar()
        layout.addWidget(self.preview_bar)

        # Action Buttons
        btn_box = QHBoxLayout()
        btn_box.setSpacing(12)

        self.btn_save = QPushButton("💾   Save Calibration")
        self.btn_save.setObjectName("btnStart")

        self.btn_recalibrate = QPushButton("🔄   Recalibrate")
        self.btn_recalibrate.setObjectName("btnCalibrate")

        self.btn_cancel = QPushButton("✕   Cancel")
        self.btn_cancel.setObjectName("btnExit")

        btn_box.addWidget(self.btn_save)
        btn_box.addWidget(self.btn_recalibrate)
        btn_box.addStretch()
        btn_box.addWidget(self.btn_cancel)

        layout.addLayout(btn_box)

        # Connections
        self.btn_save.clicked.connect(self.save_requested.emit)
        self.btn_recalibrate.clicked.connect(self.recalibrate_requested.emit)
        self.btn_cancel.clicked.connect(self.cancel_requested.emit)

    def set_calibration_data(self, data: CalibrationData) -> None:
        """Update review screen with captured calibration parameters."""
        if not data:
            return

        self.val_center.setText(f"{data.center_angle:+.1f}°")
        self.val_left.setText(f"{data.left_limit:+.1f}°")
        self.val_right.setText(f"{data.right_limit:+.1f}°")
        self.val_range.setText(f"{data.steering_range:.1f}°")
        self.val_thresh.setText(f"{data.minimum_threshold:.1f}°")

    def update_test_steering(self, norm_val: float) -> None:
        """Update live normalized steering response preview bar."""
        self.preview_bar.set_value(norm_val)
