"""
gesturedrive.gui.stats_widget
=============================
PipelineStatsWidget: Displays live camera FPS, processing FPS, frame latency (ms), and tracking confidence.
"""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QVBoxLayout


class PipelineStatsWidget(QFrame):
    """
    Widget displaying real-time performance telemetry and latency metrics.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("statusCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        # Header Title
        lbl_title = QLabel("PIPELINE PERFORMANCE STATS")
        lbl_title.setObjectName("telemetryLabel")
        layout.addWidget(lbl_title)

        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(6)

        # Row 0: Camera FPS | Processing FPS
        lbl_cam_fps = QLabel("Camera FPS:")
        lbl_cam_fps.setStyleSheet("color: #8f96a3; font-size: 11px; font-weight: 600;")
        self.val_cam_fps = QLabel("0.0")
        self.val_cam_fps.setMinimumWidth(50)
        self.val_cam_fps.setStyleSheet("color: #00e676; font-weight: 700; font-size: 14px;")

        lbl_proc_fps = QLabel("Proc FPS:")
        lbl_proc_fps.setStyleSheet("color: #8f96a3; font-size: 11px; font-weight: 600;")
        self.val_proc_fps = QLabel("0.0")
        self.val_proc_fps.setMinimumWidth(50)
        self.val_proc_fps.setStyleSheet("color: #00e5ff; font-weight: 700; font-size: 14px;")

        grid.addWidget(lbl_cam_fps, 0, 0)
        grid.addWidget(self.val_cam_fps, 0, 1)
        grid.addWidget(lbl_proc_fps, 0, 2)
        grid.addWidget(self.val_proc_fps, 0, 3)

        # Row 1: Latency | Tracking Conf
        lbl_lat = QLabel("Frame Latency:")
        lbl_lat.setStyleSheet("color: #8f96a3; font-size: 11px; font-weight: 600;")
        self.val_latency = QLabel("0.0 ms")
        self.val_latency.setMinimumWidth(55)
        self.val_latency.setStyleSheet("color: #ffb300; font-weight: 700; font-size: 14px;")

        lbl_trk_conf = QLabel("Track Conf:")
        lbl_trk_conf.setStyleSheet("color: #8f96a3; font-size: 11px; font-weight: 600;")
        self.val_trk_conf = QLabel("N/A")
        self.val_trk_conf.setMinimumWidth(50)
        self.val_trk_conf.setStyleSheet("color: #ffffff; font-weight: 700; font-size: 14px;")

        grid.addWidget(lbl_lat, 1, 0)
        grid.addWidget(self.val_latency, 1, 1)
        grid.addWidget(lbl_trk_conf, 1, 2)
        grid.addWidget(self.val_trk_conf, 1, 3)

        layout.addLayout(grid)

    def update_stats(
        self, camera_fps: float, proc_fps: float, latency_ms: float, tracking_conf: float
    ) -> None:
        """Update live camera FPS, processing FPS, latency, and tracking confidence."""
        self.val_cam_fps.setText(f"{camera_fps:.1f}")
        self.val_proc_fps.setText(f"{proc_fps:.1f}")
        self.val_latency.setText(f"{latency_ms:.1f} ms")

        if tracking_conf > 0.0:
            conf_pct = int(round(tracking_conf * 100))
            self.val_trk_conf.setText(f"{conf_pct}%")
        else:
            self.val_trk_conf.setText("N/A")
