"""
gesturedrive.gui.help_dialog
=============================
HelpCenterDialog: Modern, searchable documentation center window.

Features
--------
- Dual-pane layout: Left navigation list + Right scrollable rich HTML viewer.
- Live instant search filtering across titles and section contents.
- Dynamic keyword highlighting in search results.
- Export documentation as self-contained HTML file.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QTextDocument
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from gui.help_content import get_help_sections

logger = logging.getLogger(__name__)

_DARK_THEME_CSS = """
<style>
    body {
        background-color: #12141d;
        color: #e0e6ed;
        font-family: 'Segoe UI', Arial, sans-serif;
        font-size: 13px;
        line-height: 1.6;
        padding: 16px;
    }
    h2 {
        color: #00e5ff;
        border-bottom: 2px solid #282c3c;
        padding-bottom: 6px;
        font-size: 18px;
        margin-top: 0px;
    }
    h3 {
        color: #ffb300;
        font-size: 14px;
        margin-top: 12px;
        margin-bottom: 6px;
    }
    p.lead {
        font-size: 14px;
        color: #8f96a3;
    }
    .card {
        background-color: #1a1d28;
        border: 1px solid #282c3c;
        border-radius: 8px;
        padding: 14px;
        margin-bottom: 14px;
    }
    table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 8px;
        margin-bottom: 8px;
    }
    th {
        background-color: #242838;
        color: #00e5ff;
        text-align: left;
        padding: 8px;
        font-weight: bold;
        border: 1px solid #282c3c;
    }
    td {
        padding: 8px;
        border: 1px solid #282c3c;
        color: #e0e6ed;
    }
    tr:nth-child(even) {
        background-color: #141722;
    }
    code {
        background-color: #242838;
        color: #00e676;
        padding: 2px 6px;
        border-radius: 4px;
        font-family: Consolas, monospace;
    }
    .badge {
        background-color: #00e5ff22;
        color: #00e5ff;
        border: 1px solid #00e5ff;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: bold;
    }
    .step-list li {
        margin-bottom: 10px;
    }
    .highlight {
        background-color: #ffb300;
        color: #000000;
        font-weight: bold;
        padding: 1px 4px;
        border-radius: 2px;
    }
</style>
"""


from core.resources import apply_app_icon
from core.version import get_window_title

logger = logging.getLogger(__name__)


class HelpCenterDialog(QDialog):
    """
    Searchable Help & Documentation Dialog Window.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(get_window_title("Help Center"))
        apply_app_icon(self)
        self.resize(960, 640)
        self.setMinimumSize(800, 500)
        self.setStyleSheet("QDialog { background-color: #0b0c10; color: #ffffff; }")

        self._sections = get_help_sections()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # ── Header Toolbar ──────────────────────────────────────────────────
        header = QHBoxLayout()
        header.setSpacing(12)

        lbl_title = QLabel("📖   HELP & DOCUMENTATION CENTER")
        lbl_title.setStyleSheet("color: #00e5ff; font-weight: 800; font-size: 15px; letter-spacing: 1px;")

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍  Search documentation (e.g. steering, gestures, profiles, camera)...")
        self.txt_search.setStyleSheet(
            "QLineEdit { background-color: #1a1d28; color: #ffffff; border: 1px solid #282c3c; "
            "border-radius: 6px; padding: 6px 12px; font-size: 12px; }"
            "QLineEdit:focus { border: 1px solid #00e5ff; }"
        )
        self.txt_search.textChanged.connect(self._on_search_changed)

        self.btn_export = QPushButton("📤   Export HTML")
        self.btn_export.setStyleSheet(
            "QPushButton { background-color: #1a1d28; color: #00e5ff; border: 1px solid #282c3c; "
            "border-radius: 6px; padding: 6px 14px; font-weight: bold; font-size: 12px; }"
            "QPushButton:hover { background-color: #282c3c; color: #ffffff; }"
        )
        self.btn_export.clicked.connect(self._on_export)

        header.addWidget(lbl_title)
        header.addWidget(self.txt_search, stretch=1)
        header.addWidget(self.btn_export)
        layout.addLayout(header)

        # ── Dual-Pane Splitter Layout ───────────────────────────────────────
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background-color: #282c3c; width: 2px; }")

        # Left Navigation List
        self.nav_list = QListWidget()
        self.nav_list.setFixedWidth(240)
        self.nav_list.setStyleSheet(
            "QListWidget { background-color: #12141d; border: 1px solid #282c3c; border-radius: 8px; padding: 4px; }"
            "QListWidget::item { padding: 10px 12px; border-bottom: 1px solid #1a1d28; color: #8f96a3; font-weight: 600; font-size: 12px; border-radius: 4px; }"
            "QListWidget::item:selected { background-color: #1a1d28; color: #00e5ff; font-weight: 700; border-left: 3px solid #00e5ff; }"
            "QListWidget::item:hover { background-color: #181b26; color: #ffffff; }"
        )
        self.nav_list.currentRowChanged.connect(self._on_section_selected)

        # Populate Nav List
        for idx, sec in enumerate(self._sections):
            item = QListWidgetItem(f"{sec['icon']}  {sec['title']}")
            item.setData(Qt.UserRole, idx)
            self.nav_list.addItem(item)

        # Right Content Viewer
        self.viewer = QTextBrowser()
        self.viewer.setOpenExternalLinks(True)
        self.viewer.setStyleSheet(
            "QTextBrowser { background-color: #12141d; border: 1px solid #282c3c; border-radius: 8px; padding: 8px; }"
        )

        splitter.addWidget(self.nav_list)
        splitter.addWidget(self.viewer)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter, stretch=1)

        # Select first section by default
        if self._sections:
            self.nav_list.setCurrentRow(0)

    def _on_section_selected(self, row: int) -> None:
        """Display selected documentation section."""
        if row < 0 or row >= len(self._sections):
            return

        sec = self._sections[row]
        query = self.txt_search.text().strip().lower()

        html_body = sec["html"]
        if query:
            # Highlight keyword occurrences safely in html
            import re
            pattern = re.compile(re.escape(query), re.IGNORECASE)
            html_body = pattern.sub(lambda m: f"<span class='highlight'>{m.group(0)}</span>", html_body)

        full_html = f"<html><head>{_DARK_THEME_CSS}</head><body>{html_body}</body></html>"
        self.viewer.setHtml(full_html)

    def _on_search_changed(self, text: str) -> None:
        """Filter navigation sidebar and update search highlights."""
        query = text.strip().lower()

        matched_count = 0
        first_matched_row = -1

        for i in range(self.nav_list.count()):
            item = self.nav_list.item(i)
            idx = item.data(Qt.UserRole)
            sec = self._sections[idx]

            title_match = query in sec["title"].lower()
            content_match = query in sec["html"].lower()
            match = title_match or content_match or not query

            item.setHidden(not match)
            if match:
                matched_count += 1
                if first_matched_row == -1:
                    first_matched_row = i

        if query and first_matched_row != -1:
            self.nav_list.setCurrentRow(first_matched_row)
        elif not query and self.nav_list.currentRow() == -1:
            self.nav_list.setCurrentRow(0)
        else:
            self._on_section_selected(self.nav_list.currentRow())

    def _on_export(self) -> None:
        """Export complete documentation as a standalone HTML file."""
        filePath, _ = QFileDialog.getSaveFileName(
            self,
            "Export Help Center Documentation",
            "DriveByGesture_Help_Center.html",
            "HTML Documents (*.html)",
        )
        if not filePath:
            return

        try:
            full_doc_body = ""
            for sec in self._sections:
                full_doc_body += f"<div class='section-block'>{sec['html']}</div><hr style='border-color: #282c3c; margin: 30px 0;'>\n"

            export_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>DriveByGesture — Complete Help & Documentation</title>
    {_DARK_THEME_CSS}
</head>
<body>
    <div style="text-align: center; margin-bottom: 30px;">
        <h1 style="color: #00e5ff;">DriveByGesture Help Center</h1>
        <p style="color: #8f96a3;">Complete User Guide & System Reference Manual</p>
    </div>
    {full_doc_body}
</body>
</html>"""

            Path(filePath).write_text(export_html, encoding="utf-8")
            QMessageBox.information(
                self,
                "Export Successful",
                f"Documentation successfully exported to:\n{filePath}",
            )
        except Exception as exc:
            logger.error("Failed to export documentation: %s", exc)
            QMessageBox.critical(self, "Export Error", f"Failed to export documentation:\n{exc}")
