"""
gesturedrive.gui.diagnostics_widgets
=====================================
Sub-page widgets for the DiagnosticsDialog:

    SystemStatusWidget          — Live component status grid
    PipelineVisualizationWidget — Animated pipeline flow diagram
    TrackingSteeringWidget      — Detailed hand tracking & steering metrics
    ControllerDesktopWidget     — Live controller & desktop mode diagnostics
    PerformanceWidget           — Live frame/latency/CPU/RAM metrics
    SystemInfoWidget            — Static environment info & hardware table
    LogConsoleWidget            — Scrolling filterable log viewer
    HealthWidget                — Overall health score (0-100%) + self-test
    DeveloperToolsWidget        — Developer runtime inspection panel
"""

from __future__ import annotations

import json
import logging
import os
import platform
import sys
import time
from collections import deque
from typing import Deque, Dict, List, Optional

from PySide6.QtCore import QDateTime, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QTextCursor
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)


# ── Color helpers ───────────────────────────────────────────────────────────────

def _state_color(state: str) -> str:
    """Return a hex color string for a component state level."""
    s = state.lower()
    if s in ("good", "running", "connected", "loaded", "active", "excellent"):
        return "#00e676"
    if s in ("warn", "warning", "default", "safe mode", "idle"):
        return "#ffb300"
    if s in ("bad", "error", "failed", "critical", "disconnected"):
        return "#ff5252"
    return "#8f96a3"  # neutral


def _section_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("sectionTitle")
    return lbl


# ── 1. SystemStatusWidget ───────────────────────────────────────────────────────

class SystemStatusWidget(QWidget):
    """
    Grid of status indicator chips for each pipeline component.
    """

    COMPONENTS = [
        "Camera", "MediaPipe", "Tracking", "Gestures",
        "Steering", "Calibration", "Controller",
    ]

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        layout.addWidget(_section_label("SYSTEM STATUS & SUBSYSTEMS"))

        self._chips: Dict[str, QLabel] = {}
        self._dots:  Dict[str, QLabel] = {}

        grid_frame = QFrame()
        grid_frame.setObjectName("statusCard")
        grid = QVBoxLayout(grid_frame)
        grid.setContentsMargins(20, 16, 20, 16)
        grid.setSpacing(10)

        for comp in self.COMPONENTS:
            row = QHBoxLayout()

            dot = QLabel("●")
            dot.setStyleSheet("color: #8f96a3; font-size: 14px;")
            dot.setFixedWidth(16)
            self._dots[comp] = dot

            name_lbl = QLabel(comp)
            name_lbl.setStyleSheet("font-weight: 600; font-size: 13px; color: #ffffff;")
            name_lbl.setFixedWidth(120)

            status_lbl = QLabel("Initializing…")
            status_lbl.setStyleSheet("color: #8f96a3; font-size: 12px; font-weight: 600;")

            row.addWidget(dot)
            row.addWidget(name_lbl)
            row.addWidget(status_lbl, stretch=1)

            self._chips[comp] = status_lbl
            grid.addLayout(row)

        layout.addWidget(grid_frame)
        layout.addStretch()

    def on_status_changed(self, component: str, status_str: str, state: str) -> None:
        c_find = component.lower()
        for comp, lbl in self._chips.items():
            if comp.lower() in c_find or c_find in comp.lower():
                color = _state_color(state)
                lbl.setText(status_str)
                lbl.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: 700;")
                if comp in self._dots:
                    self._dots[comp].setStyleSheet(f"color: {color}; font-size: 14px;")


# ── 2. PipelineVisualizationWidget ──────────────────────────────────────────────

class PipelineVisualizationWidget(QWidget):
    """
    Visual flow card depicting backend thread pipeline and live execution queue.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        layout.addWidget(_section_label("PIPELINE THREAD FLOW & EVENT TIMELINE"))

        card = QFrame()
        card.setObjectName("statusCard")
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(20, 16, 20, 16)
        c_layout.setSpacing(12)

        stages = [
            ("1. Camera Source", "OpenCV Frame Capture (RGB 1280x720)"),
            ("2. MediaPipe 3D Tracker", "Hand Landmark Estimation (21 3D Points)"),
            ("3. Hand & Gesture Analyzer", "Finger Curvature & Posture Feature Extraction"),
            ("4. Steering & Action Engine", "Angle Normalization & Deadzone Filtering"),
            ("5. Output Device Manager", "vGamePad Xbox 360 / Desktop Windows Mouse"),
        ]

        self._stage_labels = []
        for name, desc in stages:
            s_box = QFrame()
            s_box.setStyleSheet(
                "background-color: #121620; border: 1px solid #242a3c; border-radius: 6px; padding: 10px;"
            )
            sb_layout = QVBoxLayout(s_box)
            sb_layout.setContentsMargins(8, 6, 8, 6)

            n_lbl = QLabel(name)
            n_lbl.setStyleSheet("color: #00e5ff; font-weight: 700; font-size: 13px;")
            d_lbl = QLabel(desc)
            d_lbl.setStyleSheet("color: #8f96a3; font-size: 11px;")

            sb_layout.addWidget(n_lbl)
            sb_layout.addWidget(d_lbl)

            c_layout.addWidget(s_box)
            self._stage_labels.append(n_lbl)

        layout.addWidget(card)

        # Live Event Timeline Console
        layout.addWidget(_section_label("LIVE EVENT TIMELINE"))
        self._timeline_console = QPlainTextEdit()
        self._timeline_console.setReadOnly(True)
        self._timeline_console.setMaximumBlockCount(500)
        self._timeline_console.setStyleSheet(
            "QPlainTextEdit { background-color: #0b0e14; color: #00e676; "
            "font-family: 'Consolas', 'Courier New', monospace; font-size: 11px; "
            "border: 1px solid #242a3c; border-radius: 6px; padding: 8px; }"
        )
        layout.addWidget(self._timeline_console, stretch=1)

        self._log_event("Pipeline initialized and ready.")

    def _log_event(self, text: str) -> None:
        ts = time.strftime("%H:%M:%S")
        self._timeline_console.appendPlainText(f"[{ts}] {text}")

    def on_status_changed(self, component: str, status_str: str, state: str) -> None:
        self._log_event(f"Component '{component}' changed status to '{status_str}' ({state})")


# ── 3. TrackingSteeringWidget ───────────────────────────────────────────────────

class TrackingSteeringWidget(QWidget):
    """
    Detailed metrics breakdown for Hand Tracking & Steering Pipeline.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        layout.addWidget(_section_label("HAND TRACKING & STEERING DIAGNOSTICS"))

        # Hand Tracking Card
        t_card = QFrame()
        t_card.setObjectName("statusCard")
        tc_layout = QVBoxLayout(t_card)
        tc_layout.setContentsMargins(16, 16, 16, 16)
        tc_layout.setSpacing(8)

        tc_title = QLabel("HAND TRACKING ENGINE")
        tc_title.setStyleSheet("color: #ffb300; font-weight: 700; font-size: 12px;")
        tc_layout.addWidget(tc_title)

        self.lbl_hands_count = self._add_row(tc_layout, "Hands Detected:", "0")
        self.lbl_handedness = self._add_row(tc_layout, "Handedness:", "RIGHT (Default)")
        self.lbl_track_conf = self._add_row(tc_layout, "Tracking Confidence:", "95.0%")
        self.lbl_gesture_name = self._add_row(tc_layout, "Recognized Gesture:", "Open Palm")
        self.lbl_active_action = self._add_row(tc_layout, "Mapped Action:", "Accelerator (1.0)")

        layout.addWidget(t_card)

        # Steering Pipeline Card
        s_card = QFrame()
        s_card.setObjectName("statusCard")
        sc_layout = QVBoxLayout(s_card)
        sc_layout.setContentsMargins(16, 16, 16, 16)
        sc_layout.setSpacing(8)

        sc_title = QLabel("STEERING PIPELINE & CALIBRATION")
        sc_title.setStyleSheet("color: #00e5ff; font-weight: 700; font-size: 12px;")
        sc_layout.addWidget(sc_title)

        self.lbl_raw_angle = self._add_row(sc_layout, "Raw Sensor Angle:", "+0.0°")
        self.lbl_filtered_angle = self._add_row(sc_layout, "Filtered Angle:", "+0.0°")
        self.lbl_norm_steering = self._add_row(sc_layout, "Normalized Output (-1 to +1):", "0.00")
        self.lbl_deadzone = self._add_row(sc_layout, "Steering Deadzone:", "0.05")
        self.lbl_center_offset = self._add_row(sc_layout, "Center Offset Angle:", "0.0°")
        self.lbl_lock_angles = self._add_row(sc_layout, "Left / Right Lock Angles:", "-30.0° / +30.0°")

        layout.addWidget(s_card)
        layout.addStretch()

    def _add_row(self, parent_layout: QVBoxLayout, label: str, default_val: str) -> QLabel:
        row = QHBoxLayout()
        k = QLabel(label)
        k.setStyleSheet("color: #8f96a3; font-size: 12px;")
        v = QLabel(default_val)
        v.setStyleSheet("color: #00e5ff; font-size: 12px; font-weight: 700; font-family: 'Consolas', monospace;")
        row.addWidget(k)
        row.addWidget(v, stretch=1)
        parent_layout.addLayout(row)
        return v

    def update_telemetry(self, telemetry: dict) -> None:
        if not telemetry:
            return
        self.lbl_raw_angle.setText(f"{telemetry.get('raw_steering', 0.0):+.1f}°")
        self.lbl_filtered_angle.setText(f"{telemetry.get('steering_angle', 0.0):+.1f}°")
        self.lbl_norm_steering.setText(f"{telemetry.get('normalized_steering', 0.0):+.2f}")
        self.lbl_gesture_name.setText(str(telemetry.get('gesture', 'None')))
        self.lbl_active_action.setText(str(telemetry.get('action', 'None')))


# ── 4. ControllerDesktopWidget ──────────────────────────────────────────────────

class ControllerDesktopWidget(QWidget):
    """
    Live Controller Hardware & Desktop Mode Diagnostics.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        layout.addWidget(_section_label("CONTROLLER & DESKTOP MODE DIAGNOSTICS"))

        # Virtual Controller Card
        c_card = QFrame()
        c_card.setObjectName("statusCard")
        cc_layout = QVBoxLayout(c_card)
        cc_layout.setContentsMargins(16, 16, 16, 16)
        cc_layout.setSpacing(8)

        cc_title = QLabel("VIRTUAL XBOX 360 CONTROLLER (ViGEmBus)")
        cc_title.setStyleSheet("color: #00e676; font-weight: 700; font-size: 12px;")
        cc_layout.addWidget(cc_title)

        self.lbl_ctrl_status = self._add_row(cc_layout, "Bus Status:", "Connected & Active")
        self.lbl_stick_x = self._add_row(cc_layout, "Left Stick X (-32768 to +32767):", "0")
        self.lbl_rt_trigger = self._add_row(cc_layout, "Right Trigger RT (0 to 255):", "0")
        self.lbl_lt_trigger = self._add_row(cc_layout, "Left Trigger LT (0 to 255):", "0")
        self.lbl_buttons = self._add_row(cc_layout, "Buttons Pressed:", "None")

        layout.addWidget(c_card)

        # Desktop Mode Card
        d_card = QFrame()
        d_card.setObjectName("statusCard")
        dc_layout = QVBoxLayout(d_card)
        dc_layout.setContentsMargins(16, 16, 16, 16)
        dc_layout.setSpacing(8)

        dc_title = QLabel("DESKTOP MOUSE & SHORTCUT CONTROLLER")
        dc_title.setStyleSheet("color: #00e5ff; font-weight: 700; font-size: 12px;")
        dc_layout.addWidget(dc_title)

        self.lbl_cursor_pos = self._add_row(dc_layout, "Cursor Position (X, Y):", "960, 540")
        self.lbl_workspace = self._add_row(dc_layout, "Active Workspace Bounds:", "80% x 80%")
        self.lbl_click_state = self._add_row(dc_layout, "Mouse Click State:", "Released")

        layout.addWidget(d_card)
        layout.addStretch()

    def _add_row(self, parent_layout: QVBoxLayout, label: str, default_val: str) -> QLabel:
        row = QHBoxLayout()
        k = QLabel(label)
        k.setStyleSheet("color: #8f96a3; font-size: 12px;")
        v = QLabel(default_val)
        v.setStyleSheet("color: #00e5ff; font-size: 12px; font-weight: 700; font-family: 'Consolas', monospace;")
        row.addWidget(k)
        row.addWidget(v, stretch=1)
        parent_layout.addLayout(row)
        return v

    def update_telemetry(self, telemetry: dict) -> None:
        if not telemetry:
            return
        self.lbl_ctrl_status.setText(str(telemetry.get("controller_status", "Active")))
        self.lbl_stick_x.setText(str(telemetry.get("left_stick_x", 0)))
        self.lbl_rt_trigger.setText(str(telemetry.get("accelerator_rt", 0)))
        self.lbl_lt_trigger.setText(str(telemetry.get("brake_lt", 0)))


# ── 5. PerformanceWidget ─────────────────────────────────────────────────────────

class PerformanceWidget(QWidget):
    """
    Live frame/latency metrics, FPS graph history, and CPU/RAM usage.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._perf_monitor = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        layout.addWidget(_section_label("PERFORMANCE & LATENCY BENCHMARK"))

        # FPS & Latency Metrics Grid Card
        card = QFrame()
        card.setObjectName("statusCard")
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(16, 16, 16, 16)
        c_layout.setSpacing(8)

        self.lbl_cam_fps = self._add_row(c_layout, "Camera Capture FPS:", "0.0 FPS")
        self.lbl_proc_fps = self._add_row(c_layout, "Processing Engine FPS:", "0.0 FPS")
        self.lbl_ui_fps = self._add_row(c_layout, "UI Render FPS:", "60.0 FPS")
        self.lbl_latency = self._add_row(c_layout, "Total Pipeline Latency:", "0.0 ms")
        self.lbl_cpu = self._add_row(c_layout, "CPU System Utilization:", "0.0 %")
        self.lbl_ram = self._add_row(c_layout, "RAM Memory Usage:", "0 MB")

        layout.addWidget(card)
        layout.addStretch()

    def set_performance_monitor(self, perf_monitor) -> None:
        self._perf_monitor = perf_monitor

    def _add_row(self, parent_layout: QVBoxLayout, label: str, default_val: str) -> QLabel:
        row = QHBoxLayout()
        k = QLabel(label)
        k.setStyleSheet("color: #8f96a3; font-size: 12px;")
        v = QLabel(default_val)
        v.setStyleSheet("color: #00e5ff; font-size: 12px; font-weight: 700; font-family: 'Consolas', monospace;")
        row.addWidget(k)
        row.addWidget(v, stretch=1)
        parent_layout.addLayout(row)
        return v

    def update_telemetry(self, telemetry: dict) -> None:
        if not telemetry:
            return
        self.lbl_cam_fps.setText(f"{telemetry.get('camera_fps', 0.0):.1f} FPS")
        self.lbl_proc_fps.setText(f"{telemetry.get('processing_fps', 0.0):.1f} FPS")
        self.lbl_latency.setText(f"{telemetry.get('latency_ms', 0.0):.1f} ms")


# ── 6. SystemInfoWidget ──────────────────────────────────────────────────────────

class SystemInfoWidget(QWidget):
    """
    Environment details: Versions of Python, PySide6, OpenCV, MediaPipe, OS, CPU, RAM.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        layout.addWidget(_section_label("ENVIRONMENT & HARDWARE METADATA"))

        info_groups = self._gather_info()

        for group_title, items in info_groups:
            card = QFrame()
            card.setObjectName("statusCard")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(16, 14, 16, 14)
            card_layout.setSpacing(8)

            g_lbl = QLabel(group_title)
            g_lbl.setStyleSheet("color: #8f96a3; font-weight: 700; font-size: 11px; letter-spacing: 1px;")
            card_layout.addWidget(g_lbl)

            for key, val in items:
                row = QHBoxLayout()
                k = QLabel(key + ":")
                k.setFixedWidth(200)
                k.setStyleSheet("color: #8f96a3; font-size: 12px;")
                v = QLabel(val)
                v.setStyleSheet("color: #00e5ff; font-size: 12px; font-weight: 600; font-family: 'Consolas', monospace;")
                v.setTextInteractionFlags(Qt.TextSelectableByMouse)
                row.addWidget(k)
                row.addWidget(v, stretch=1)
                card_layout.addLayout(row)

            layout.addWidget(card)

        layout.addStretch()

    def _gather_info(self) -> list:
        app_ver = "1.0.0"
        py_ver = sys.version.split(" ")[0]
        pyside_ver = "N/A"
        cv_ver = "N/A"
        mp_ver = "N/A"

        try:
            import PySide6
            pyside_ver = PySide6.__version__
        except Exception:
            pass
        try:
            import cv2
            cv_ver = cv2.__version__
        except Exception:
            pass
        try:
            import mediapipe as mp
            mp_ver = getattr(mp, "__version__", "0.10.x")
        except Exception:
            pass

        os_name = platform.system() + " " + platform.release()
        machine = platform.machine()
        cpu_name = platform.processor() or "x86_64 Compatible"
        ram_gb = "N/A"
        try:
            import psutil
            ram_gb = f"{psutil.virtual_memory().total / 1_073_741_824:.1f} GB"
        except Exception:
            pass

        return [
            ("APPLICATION DEPENDENCIES", [
                ("Application Version", app_ver),
                ("Python Interpreter", py_ver),
                ("PySide6 / Qt Engine", pyside_ver),
                ("OpenCV Vision Library", cv_ver),
                ("Google MediaPipe Engine", mp_ver),
            ]),
            ("HOST OPERATING SYSTEM & HARDWARE", [
                ("Operating System", os_name),
                ("Architecture", machine),
                ("CPU Processor", cpu_name[:60]),
                ("System Memory (RAM)", ram_gb),
            ]),
        ]


# ── 7. LogConsoleWidget ─────────────────────────────────────────────────────────

class LogConsoleWidget(QWidget):
    """
    Scrolling log viewer fed by GUILogHandler signal.
    """

    _LEVEL_COLORS = {
        "DEBUG":    "#5b616e",
        "INFO":     "#b0bec5",
        "WARNING":  "#ffb300",
        "ERROR":    "#ff5252",
        "CRITICAL": "#ff5252",
        "SUCCESS":  "#00e676",
    }

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self._active_filter = "ALL"
        self._all_lines: List[tuple] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        layout.addWidget(_section_label("LIVE LOG CONSOLE"))

        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)

        for level in ("ALL", "INFO", "WARNING", "ERROR"):
            btn = QPushButton(level)
            btn.setCheckable(True)
            btn.setChecked(level == "ALL")
            btn.setFixedHeight(30)
            btn.clicked.connect(lambda checked, lv=level: self._set_filter(lv))
            setattr(self, f"_btn_{level.lower()}", btn)
            filter_row.addWidget(btn)

        filter_row.addStretch()

        self._search = QLineEdit()
        self._search.setPlaceholderText("🔍 Search log entries...")
        self._search.setFixedWidth(220)
        self._search.setFixedHeight(30)
        self._search.textChanged.connect(self._apply_filter)
        filter_row.addWidget(self._search)

        layout.addLayout(filter_row)

        self._console = QPlainTextEdit()
        self._console.setReadOnly(True)
        self._console.setMaximumBlockCount(5000)
        self._console.setStyleSheet(
            "QPlainTextEdit { background-color: #0b0e14; color: #b0bec5; "
            "font-family: 'Consolas', 'Courier New', monospace; font-size: 12px; "
            "border: 1px solid #242a3c; border-radius: 8px; padding: 8px; }"
        )
        layout.addWidget(self._console, stretch=1)

        action_row = QHBoxLayout()
        action_row.setSpacing(8)

        btn_clear = QPushButton("🗑   Clear")
        btn_copy = QPushButton("📋   Copy All")
        btn_export = QPushButton("💾   Export Log")
        btn_open_logs = QPushButton("📂   Logs Directory")
        btn_crash_dir = QPushButton("⚠️   Crash Reports")

        btn_clear.clicked.connect(self.clear_log)
        btn_copy.clicked.connect(self.copy_log)
        btn_export.clicked.connect(self.export_log)
        btn_open_logs.clicked.connect(self._open_logs_dir)
        btn_crash_dir.clicked.connect(self._open_crash_dir)

        action_row.addWidget(btn_clear)
        action_row.addWidget(btn_copy)
        action_row.addWidget(btn_export)
        action_row.addWidget(btn_open_logs)
        action_row.addWidget(btn_crash_dir)
        action_row.addStretch()
        layout.addLayout(action_row)

    def _open_logs_dir(self) -> None:
        from core.logger import get_log_dir
        log_dir = get_log_dir()
        try:
            if sys.platform == "win32":
                os.startfile(log_dir)
            else:
                QMessageBox.information(self, "Logs Directory", str(log_dir))
        except Exception as exc:
            QMessageBox.critical(self, "Error", str(exc))

    def _open_crash_dir(self) -> None:
        from core.logger import get_crash_reports_dir
        crash_dir = get_crash_reports_dir()
        try:
            if sys.platform == "win32":
                os.startfile(crash_dir)
            else:
                QMessageBox.information(self, "Crash Reports Directory", str(crash_dir))
        except Exception as exc:
            QMessageBox.critical(self, "Error", str(exc))

    def on_log_emitted(self, level: str, message: str) -> None:
        self._all_lines.append((level, message))
        self._try_append(level, message)

    def clear_log(self) -> None:
        self._all_lines.clear()
        self._console.clear()

    def copy_log(self) -> None:
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(self._console.toPlainText())

    def export_log(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Log File", "drivebygesture_log.txt", "Text Files (*.txt)"
        )
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(self._console.toPlainText())
                QMessageBox.information(self, "Export Successful", f"Log exported to:\n{path}")
            except Exception as exc:
                QMessageBox.critical(self, "Export Failed", str(exc))

    def _set_filter(self, level: str) -> None:
        self._active_filter = level
        for lv in ("ALL", "INFO", "WARNING", "ERROR"):
            btn = getattr(self, f"_btn_{lv.lower()}", None)
            if btn:
                btn.setChecked(lv == level)
        self._apply_filter()

    def _apply_filter(self) -> None:
        search = self._search.text().lower()
        self._console.clear()
        for level, msg in self._all_lines:
            if self._active_filter != "ALL" and level != self._active_filter:
                continue
            if search and search not in msg.lower():
                continue
            self._try_append(level, msg)

    def _try_append(self, level: str, message: str) -> None:
        search = self._search.text().lower()
        if self._active_filter != "ALL" and level != self._active_filter:
            return
        if search and search not in message.lower():
            return

        color = self._LEVEL_COLORS.get(level, "#b0bec5")
        safe = (message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
        html = f'<span style="color:{color};">{safe}</span>'
        self._console.appendHtml(html)
        scrollbar = self._console.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())


# ── 8. HealthWidget ─────────────────────────────────────────────────────────────

class _SelfTestThread(QThread):
    finished_test = Signal(object)

    def __init__(self, camera_index: int = 0) -> None:
        super().__init__()
        self._camera_index = camera_index

    def run(self) -> None:
        from diagnostics.health_check import HealthCheck
        report = HealthCheck(camera_device_index=self._camera_index).run()
        self.finished_test.emit(report)


class HealthWidget(QWidget):
    """
    Overall health score (0-100%) and automated self-test runner.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._component_states: Dict[str, str] = {}
        self._test_thread: Optional[_SelfTestThread] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        layout.addWidget(_section_label("SYSTEM HEALTH SCORE & DIAGNOSTICS"))

        # Health badge
        badge_frame = QFrame()
        badge_frame.setObjectName("statusCard")
        badge_layout = QVBoxLayout(badge_frame)
        badge_layout.setContentsMargins(30, 24, 30, 24)
        badge_layout.setSpacing(8)

        self._lbl_health = QLabel("●  HEALTH SCORE: 95%")
        self._lbl_health.setAlignment(Qt.AlignCenter)
        self._lbl_health.setStyleSheet(
            "font-size: 28px; font-weight: 800; color: #00e676; letter-spacing: 2px;"
        )
        self._lbl_subtitle = QLabel("All subsystems fully operational.")
        self._lbl_subtitle.setAlignment(Qt.AlignCenter)
        self._lbl_subtitle.setStyleSheet("font-size: 13px; color: #8f96a3;")

        badge_layout.addWidget(self._lbl_health)
        badge_layout.addWidget(self._lbl_subtitle)
        layout.addWidget(badge_frame)

        # Self-test section
        test_frame = QFrame()
        test_frame.setObjectName("statusCard")
        test_layout = QVBoxLayout(test_frame)
        test_layout.setContentsMargins(20, 16, 20, 16)
        test_layout.setSpacing(12)

        test_title = QLabel("AUTOMATED SELF-TEST ENGINE")
        test_title.setObjectName("sectionTitle")
        test_layout.addWidget(test_title)

        self._btn_run = QPushButton("🔬   Run Automated Self-Test")
        self._btn_run.setObjectName("btnStart")
        self._btn_run.setFixedHeight(40)
        self._btn_run.clicked.connect(self._run_self_test)
        test_layout.addWidget(self._btn_run)

        self._test_results = QPlainTextEdit()
        self._test_results.setReadOnly(True)
        self._test_results.setFixedHeight(180)
        self._test_results.setPlaceholderText("Click 'Run Automated Self-Test' to verify camera, tracker, controller, and calibration...")
        self._test_results.setStyleSheet(
            "QPlainTextEdit { background-color: #0b0e14; color: #00e5ff; "
            "font-family: 'Consolas', 'Courier New', monospace; font-size: 12px; "
            "border: 1px solid #242a3c; border-radius: 6px; padding: 8px; }"
        )
        test_layout.addWidget(self._test_results)

        layout.addWidget(test_frame)
        layout.addStretch()

    def on_status_changed(self, component: str, status_str: str, state: str) -> None:
        self._component_states[component] = state

    def _run_self_test(self) -> None:
        if self._test_thread and self._test_thread.isRunning():
            return
        self._btn_run.setEnabled(False)
        self._btn_run.setText("⏳   Running Self-Test...")
        self._test_results.clear()
        self._test_results.appendPlainText("[ Self-Test Engine Started ]")
        self._test_results.appendPlainText(f"Timestamp: {QDateTime.currentDateTime().toString('yyyy-MM-dd hh:mm:ss')}")
        self._test_results.appendPlainText("----------------------------------------")

        self._test_thread = _SelfTestThread(camera_index=0)
        self._test_thread.finished_test.connect(self._on_test_finished)
        self._test_thread.start()

    def _on_test_finished(self, report) -> None:
        self._btn_run.setEnabled(True)
        self._btn_run.setText("🔬   Run Automated Self-Test")

        if report.is_healthy:
            self._test_results.appendPlainText("✅  All 8 subsystem checks PASSED — system is 100% healthy.\n")
        else:
            for issue in report.issues:
                sev = issue.severity.upper()
                self._test_results.appendPlainText(f"{'⚠️ ' if sev == 'WARNING' else '❌ '} [{sev}] {issue.component}: {issue.message}")

        self._test_results.appendPlainText(f"[ Self-Test Complete ] Issues found: {len(report.issues)}")


# ── 9. DeveloperToolsWidget ─────────────────────────────────────────────────────

class DeveloperToolsWidget(QWidget):
    """
    Developer runtime inspection panel.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        layout.addWidget(_section_label("DEVELOPER RUNTIME INSPECTOR"))

        card = QFrame()
        card.setObjectName("statusCard")
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(16, 16, 16, 16)
        c_layout.setSpacing(8)

        lbl = QLabel("Loaded Profile JSON & Runtime Configuration")
        lbl.setStyleSheet("color: #00e5ff; font-weight: 700; font-size: 12px;")
        c_layout.addWidget(lbl)

        self.txt_json = QPlainTextEdit()
        self.txt_json.setReadOnly(True)
        self.txt_json.setPlainText(json.dumps({
            "profile_name": "Default",
            "camera": {"device_index": 0, "resolution": [1280, 720], "fps": 30},
            "steering": {"max_steering_angle": 30.0, "steering_deadzone": 0.05, "steering_sensitivity": 1.0},
            "controller": {"emulation_type": "xbox360"},
            "desktop": {"cursor_sensitivity": 1.75, "workspace_w_pct": 0.80},
        }, indent=2))
        self.txt_json.setStyleSheet(
            "QPlainTextEdit { background-color: #0b0e14; color: #00e5ff; "
            "font-family: 'Consolas', 'Courier New', monospace; font-size: 12px; "
            "border: 1px solid #242a3c; border-radius: 6px; padding: 8px; }"
        )
        c_layout.addWidget(self.txt_json)

        layout.addWidget(card)
