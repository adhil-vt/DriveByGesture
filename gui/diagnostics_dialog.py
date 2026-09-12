"""
gesturedrive.gui.diagnostics_dialog
=====================================
DiagnosticsDialog: Professional Diagnostics & Developer Tools Center Window.

Features
--------
- Multi-section navigation panel: Status, Tracking & Steering, Controller & Desktop, Performance, Environment, Live Log Console, Health & Self-Test, Developer Tools.
- Live real-time metric updates without pipeline modification.
- Export complete diagnostic report to JSON or TXT file.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from diagnostics.performance_monitor import PerformanceMonitor
from gui.diagnostics_widgets import (
    ControllerDesktopWidget,
    DeveloperToolsWidget,
    HealthWidget,
    LogConsoleWidget,
    PerformanceWidget,
    PipelineVisualizationWidget,
    SystemInfoWidget,
    SystemStatusWidget,
    TrackingSteeringWidget,
)
from gui.styles import DARK_THEME_QSS

from core.resources import apply_app_icon
from core.version import get_window_title

logger = logging.getLogger(__name__)


class DiagnosticsDialog(QDialog):
    """
    Professional Diagnostics and Developer Tools Center Window.
    """

    def __init__(self, worker=None, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self.setWindowTitle(get_window_title("Diagnostics"))
        apply_app_icon(self)
        self.resize(1100, 780)
        self.setMinimumSize(900, 650)
        self.setStyleSheet(DARK_THEME_QSS)
        self.setWindowFlags(
            self.windowFlags() | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint
        )

        self._worker = worker
        self._perf_monitor = PerformanceMonitor(interval_seconds=3.0)
        self._perf_monitor.start()
        self._last_telemetry: dict = {}

        # ── Root layout ────────────────────────────────────────────────────────
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Header bar
        header = QWidget()
        header.setFixedHeight(50)
        header.setStyleSheet("background: #0b0e14; border-bottom: 1px solid #1a1f2c;")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(20, 0, 20, 0)

        title_lbl = QLabel("🔬   DIAGNOSTICS & DEVELOPER CENTER")
        title_lbl.setStyleSheet(
            "font-size: 14px; font-weight: 800; color: #00e5ff; letter-spacing: 1px;"
        )
        h_layout.addWidget(title_lbl)
        h_layout.addStretch()

        btn_export = QPushButton("📤   Export Report")
        btn_export.setStyleSheet(
            "QPushButton { background-color: #1a1f2c; color: #00e5ff; border: 1px solid #242a3c; "
            "border-radius: 6px; padding: 4px 12px; font-weight: bold; font-size: 12px; height: 32px; min-height: 32px; }"
            "QPushButton:hover { background-color: #222838; color: #ffffff; }"
        )
        btn_export.clicked.connect(self._on_export_report)
        h_layout.addWidget(btn_export)

        root_layout.addWidget(header)

        # ── Main split: nav list | stacked pages ───────────────────────────────
        main_split = QSplitter(Qt.Horizontal)
        main_split.setHandleWidth(1)
        main_split.setStyleSheet("QSplitter::handle { background: #1a1f2c; }")

        # Left navigation list
        self.nav_list = QListWidget()
        self.nav_list.setFixedWidth(220)
        self.nav_list.setStyleSheet(
            """
            QListWidget {
                background: #0b0e14;
                border: none;
                padding: 8px 0;
            }
            QListWidget::item {
                padding: 12px 18px;
                color: #8f96a3;
                font-size: 13px;
                font-weight: 600;
                border-radius: 0px;
                border-left: 3px solid transparent;
            }
            QListWidget::item:selected {
                background: #121620;
                color: #00e5ff;
                border-left: 3px solid #00e5ff;
            }
            QListWidget::item:hover:!selected {
                background: #121620;
                color: #ffffff;
            }
            """
        )

        nav_items = [
            ("📊   System Status",         0),
            ("🏎️   Tracking & Steering",    1),
            ("🎮   Controller & Desktop",   2),
            ("⚡   Performance Metrics",    3),
            ("💻   Environment & Hardware", 4),
            ("📋   Live Log Console",       5),
            ("❤   Health & Self-Test",     6),
            ("🛠️   Developer Tools",        7),
        ]

        for title, idx in nav_items:
            item = QListWidgetItem(title)
            item.setData(Qt.ItemDataRole.UserRole, idx)
            self.nav_list.addItem(item)

        main_split.addWidget(self.nav_list)

        # ── Pages ──────────────────────────────────────────────────────────────
        self.pages_stack = QStackedWidget()

        self.page_status    = SystemStatusWidget()
        self.page_tracking  = TrackingSteeringWidget()
        self.page_controller = ControllerDesktopWidget()
        self.page_perf      = PerformanceWidget()
        self.page_sysinfo   = SystemInfoWidget()
        self.page_log       = LogConsoleWidget()
        self.page_health    = HealthWidget()
        self.page_devtools  = DeveloperToolsWidget()

        self.page_perf.set_performance_monitor(self._perf_monitor)

        self.pages_stack.addWidget(self.page_status)
        self.pages_stack.addWidget(self.page_tracking)
        self.pages_stack.addWidget(self.page_controller)
        self.pages_stack.addWidget(self.page_perf)
        self.pages_stack.addWidget(self.page_sysinfo)
        self.pages_stack.addWidget(self.page_log)
        self.pages_stack.addWidget(self.page_health)
        self.pages_stack.addWidget(self.page_devtools)

        main_split.addWidget(self.pages_stack)
        main_split.setSizes([220, 880])

        root_layout.addWidget(main_split, stretch=1)

        # ── Wire navigation ────────────────────────────────────────────────────
        self.nav_list.currentRowChanged.connect(self.pages_stack.setCurrentIndex)
        self.nav_list.setCurrentRow(0)

        # ── Connect handlers ───────────────────────────────────────────────────
        self._connect_log_handler()

        if worker is not None:
            self._connect_worker(worker)

        logger.info("DiagnosticsDialog opened.")

    # ── Public API called from MainWindow ─────────────────────────────────────

    def update_telemetry(self, telemetry: dict) -> None:
        """Forward live telemetry dict to sub-pages (called each frame)."""
        self._last_telemetry = telemetry or {}
        self.page_perf.update_telemetry(self._last_telemetry)
        self.page_tracking.update_telemetry(self._last_telemetry)
        self.page_controller.update_telemetry(self._last_telemetry)

    def on_status_changed(self, component: str, status_str: str, state: str) -> None:
        """Forward status change to all relevant page widgets."""
        self.page_status.on_status_changed(component, status_str, state)
        self.page_health.on_status_changed(component, status_str, state)

    # ── Internal Export ───────────────────────────────────────────────────────

    def _on_export_report(self) -> None:
        """Export comprehensive diagnostic report to JSON or TXT file."""
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export Diagnostics Report",
            f"DriveByGesture_Diagnostics_{int(time.time())}.json",
            "JSON Report (*.json);;Text Report (*.txt)",
        )
        if not file_path:
            return

        try:
            report_data = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "application": {
                    "name": "DriveByGesture",
                    "version": "1.0.0",
                    "build": "2026.08.03-RELEASE",
                },
                "telemetry": self._last_telemetry,
                "recent_logs": [f"{lvl}: {msg}" for lvl, msg in getattr(self.page_log, "_all_lines", [])[-50:]],
            }

            p = Path(file_path)
            if p.suffix.lower() == ".json":
                p.write_text(json.dumps(report_data, indent=2), encoding="utf-8")
            else:
                txt_content = f"DriveByGesture Diagnostics Report — {report_data['timestamp']}\n\n"
                txt_content += json.dumps(report_data, indent=2)
                p.write_text(txt_content, encoding="utf-8")

            QMessageBox.information(
                self,
                "Export Successful",
                f"Diagnostics report saved to:\n{file_path}",
            )
        except Exception as exc:
            logger.error("Failed to export diagnostics report: %s", exc)
            QMessageBox.critical(self, "Export Error", f"Could not export diagnostics report: {exc}")

    def _connect_log_handler(self) -> None:
        """Attach LogConsoleWidget to the global GUILogHandler emitter."""
        try:
            import logging as _logging
            root = _logging.getLogger()
            for handler in root.handlers:
                emitter = getattr(handler, "emitter", None)
                if emitter is not None and hasattr(emitter, "log_emitted"):
                    emitter.log_emitted.connect(self.page_log.on_log_emitted)
                    logger.info("DiagnosticsDialog: Log console connected to GUILogHandler.")
                    return
        except Exception as exc:
            logger.warning("DiagnosticsDialog: Could not connect to GUILogHandler: %s", exc)

    def _connect_worker(self, worker) -> None:
        """Subscribe to PipelineWorker signals non-destructively."""
        try:
            if hasattr(worker, "status_changed"):
                worker.status_changed.connect(self.on_status_changed)
        except Exception as exc:
            logger.warning("DiagnosticsDialog: Could not connect worker signals: %s", exc)

    def closeEvent(self, event) -> None:
        """Stop PerformanceMonitor on close."""
        try:
            self._perf_monitor.stop()
        except Exception:
            pass
        logger.info("DiagnosticsDialog closed.")
        super().closeEvent(event)
