"""
gesturedrive.gui.crash_dialog
===============================
CrashDialog: Production Crash Recovery Window.

Displays user-friendly error message, expandable stack trace,
and action buttons for copying report, saving report, restarting app, or exiting.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.resources import apply_app_icon
from core.version import get_window_title
from gui.styles import DARK_THEME_QSS

logger = logging.getLogger(__name__)


class CrashDialog(QDialog):
    """
    Production Crash Recovery Dialog Window.
    """

    def __init__(self, report_path: Path, report_data: dict, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self.report_path = report_path
        self.report_data = report_data

        self.setWindowTitle(get_window_title("Crash Report"))
        apply_app_icon(self)
        self.resize(720, 520)
        self.setMinimumSize(640, 440)
        self.setStyleSheet(DARK_THEME_QSS)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Header Warning Banner Card
        banner = QFrame()
        banner.setStyleSheet(
            "QFrame { background-color: #1f1214; border: 1px solid #ff5252; border-radius: 8px; padding: 14px; }"
        )
        b_layout = QHBoxLayout(banner)
        b_layout.setContentsMargins(8, 8, 8, 8)
        b_layout.setSpacing(12)

        lbl_icon = QLabel("⚠️")
        lbl_icon.setStyleSheet("font-size: 28px; border: none;")

        v_box = QVBoxLayout()
        v_box.setSpacing(4)
        lbl_h1 = QLabel("DriveByGesture Encountered an Unexpected Error")
        lbl_h1.setStyleSheet("font-size: 15px; font-weight: 800; color: #ff5252; border: none;")

        lbl_sub = QLabel("The application caught an unhandled exception and generated a crash report.")
        lbl_sub.setStyleSheet("font-size: 12px; color: #8f96a3; border: none;")

        v_box.addWidget(lbl_h1)
        v_box.addWidget(lbl_sub)

        b_layout.addWidget(lbl_icon)
        b_layout.addLayout(v_box, stretch=1)

        layout.addWidget(banner)

        # Summary Info Card
        card = QFrame()
        card.setObjectName("statusCard")
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(16, 12, 16, 12)
        c_layout.setSpacing(6)

        exc_type = report_data.get("exception_type", "Unhandled Exception")
        exc_msg = report_data.get("exception_message", "No message available.")

        self._add_info_row(c_layout, "Error Type:", exc_type)
        self._add_info_row(c_layout, "Message:", exc_msg)
        self._add_info_row(c_layout, "Report File:", str(report_path.name))

        layout.addWidget(card)

        # Expandable Traceback Console
        self.btn_toggle_details = QPushButton("🔍   Show Error Details")
        self.btn_toggle_details.setCheckable(True)
        self.btn_toggle_details.clicked.connect(self._toggle_details)
        layout.addWidget(self.btn_toggle_details)

        self.txt_traceback = QPlainTextEdit()
        self.txt_traceback.setReadOnly(True)
        self.txt_traceback.setVisible(False)
        self.txt_traceback.setPlainText(report_data.get("stack_trace", "No stack trace."))
        self.txt_traceback.setStyleSheet(
            "QPlainTextEdit { background-color: #0b0e14; color: #ff5252; "
            "font-family: 'Consolas', 'Courier New', monospace; font-size: 11px; "
            "border: 1px solid #242a3c; border-radius: 6px; padding: 8px; }"
        )
        layout.addWidget(self.txt_traceback, stretch=1)

        # Action Buttons Toolbar
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        btn_copy = QPushButton("📋   Copy Report")
        btn_save = QPushButton("💾   Save Report")
        btn_restart = QPushButton("🔄   Restart App")
        btn_exit = QPushButton("❌   Exit App")

        btn_restart.setObjectName("btnStart")
        btn_exit.setStyleSheet(
            "QPushButton { background-color: #2b1f24; color: #ff5252; border: 1px solid #ff5252; "
            "border-radius: 6px; padding: 6px 14px; font-weight: bold; font-size: 12px; height: 36px; min-height: 36px; }"
            "QPushButton:hover { background-color: #ff5252; color: #ffffff; }"
        )

        btn_copy.clicked.connect(self._copy_report)
        btn_save.clicked.connect(self._save_report)
        btn_restart.clicked.connect(self._restart_app)
        btn_exit.clicked.connect(self._exit_app)

        btn_layout.addWidget(btn_copy)
        btn_layout.addWidget(btn_save)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_restart)
        btn_layout.addWidget(btn_exit)

        layout.addLayout(btn_layout)

    def _add_info_row(self, layout: QVBoxLayout, label: str, value: str) -> None:
        row = QHBoxLayout()
        k = QLabel(label)
        k.setFixedWidth(100)
        k.setStyleSheet("color: #8f96a3; font-size: 12px; font-weight: 600;")
        v = QLabel(value)
        v.setStyleSheet("color: #ffffff; font-size: 12px; font-weight: 700; font-family: 'Consolas', monospace;")
        row.addWidget(k)
        row.addWidget(v, stretch=1)
        layout.addLayout(row)

    def _toggle_details(self, checked: bool) -> None:
        self.txt_traceback.setVisible(checked)
        self.btn_toggle_details.setText("🔍   Hide Error Details" if checked else "🔍   Show Error Details")

    def _copy_report(self) -> None:
        QApplication.clipboard().setText(json.dumps(self.report_data, indent=2))
        QMessageBox.information(self, "Copied", "Crash report copied to clipboard.")

    def _save_report(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Crash Report", str(self.report_path.name), "JSON Files (*.json);;Text Files (*.txt)"
        )
        if path:
            try:
                Path(path).write_text(json.dumps(self.report_data, indent=2), encoding="utf-8")
                QMessageBox.information(self, "Saved", f"Crash report saved to:\n{path}")
            except Exception as exc:
                QMessageBox.critical(self, "Error", str(exc))

    def _restart_app(self) -> None:
        self.accept()
        QApplication.quit()
        os.execl(sys.executable, sys.executable, *sys.argv)

    def _exit_app(self) -> None:
        self.reject()
        QApplication.quit()
