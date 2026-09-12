"""
gesturedrive.gui.profile_dialog
================================
ProfileDialog: Full-featured profile manager window.

Two-panel layout:
    Left:  QListWidget of all profiles with active highlight
    Right: Detail panel (name, description, game, author, calibration status)

CRUD buttons: Create, Rename, Duplicate, Delete, Import, Export, Activate.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from gui.styles import DARK_THEME_QSS

from core.resources import apply_app_icon
from core.version import get_window_title

logger = logging.getLogger(__name__)


class ProfileDialog(QDialog):
    """
    Profile Manager dialog (modal).
    """

    profile_activated = Signal(str)

    def __init__(self, profile_manager, active_name: str = "Default", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._manager = profile_manager
        self._active_name = active_name

        self.setWindowTitle(get_window_title("Profiles"))
        apply_app_icon(self)
        self.resize(900, 620)
        self.setMinimumSize(760, 500)
        self.setStyleSheet(DARK_THEME_QSS)

        # ── Root layout ────────────────────────────────────────────────────────
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        header = QWidget()
        header.setFixedHeight(48)
        header.setStyleSheet("background: #0d0e12; border-bottom: 1px solid #1e2030;")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(20, 0, 20, 0)
        title = QLabel("👤  Profile Manager")
        title.setStyleSheet("font-size: 14px; font-weight: 700; color: #00e5ff;")
        h_layout.addWidget(title)
        h_layout.addStretch()
        root.addWidget(header)

        # ── Main split ─────────────────────────────────────────────────────────
        split = QSplitter(Qt.Horizontal)
        split.setHandleWidth(1)
        split.setStyleSheet("QSplitter::handle { background: #1e2030; }")

        # Left panel — profile list
        left = QWidget()
        left.setFixedWidth(260)
        left.setStyleSheet("background: #0d0e12;")
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(8)

        left_title = QLabel("PROFILES")
        left_title.setStyleSheet(
            "color: #5b616e; font-size: 11px; font-weight: 700; letter-spacing: 1px; padding: 4px 0;"
        )
        left_layout.addWidget(left_title)

        self._list = QListWidget()
        self._list.setStyleSheet(
            "QListWidget { background: #0d0e12; border: none; }"
            "QListWidget::item { padding: 12px 16px; color: #8f96a3; font-size: 13px; "
            "font-weight: 600; border-radius: 8px; margin: 1px 0; }"
            "QListWidget::item:selected { background: #14161f; color: #00e5ff; "
            "border: 1px solid #00e5ff33; border-radius: 8px; }"
            "QListWidget::item:hover:!selected { background: #11131a; color: #ffffff; }"
        )
        self._list.currentItemChanged.connect(self._on_selection_changed)
        left_layout.addWidget(self._list, stretch=1)

        split.addWidget(left)

        # Right panel — detail + actions
        right = QWidget()
        right.setStyleSheet("background: #0d0e12;")
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(20, 20, 20, 20)
        right_layout.setSpacing(16)

        # Detail card
        self._detail_card = QFrame()
        self._detail_card.setObjectName("statusCard")
        detail_layout = QVBoxLayout(self._detail_card)
        detail_layout.setContentsMargins(20, 16, 20, 16)
        detail_layout.setSpacing(10)

        self._lbl_name = QLabel("Select a profile")
        self._lbl_name.setStyleSheet("font-size: 20px; font-weight: 800; color: #00e5ff;")

        self._lbl_game = QLabel("")
        self._lbl_game.setStyleSheet("font-size: 12px; color: #8f96a3;")

        self._lbl_cal = QLabel("")
        self._lbl_cal.setStyleSheet("font-size: 12px; color: #ffb300; font-weight: 600;")

        self._lbl_created = QLabel("")
        self._lbl_created.setStyleSheet("font-size: 11px; color: #5b616e;")

        self._lbl_modified = QLabel("")
        self._lbl_modified.setStyleSheet("font-size: 11px; color: #5b616e;")

        desc_label = QLabel("Description:")
        desc_label.setStyleSheet("color: #5b616e; font-size: 11px; font-weight: 600;")
        self._txt_desc = QTextEdit()
        self._txt_desc.setReadOnly(True)
        self._txt_desc.setFixedHeight(60)
        self._txt_desc.setStyleSheet(
            "QTextEdit { background: #11131a; color: #8f96a3; border: 1px solid #1e2030; "
            "border-radius: 6px; padding: 6px; font-size: 12px; }"
        )

        detail_layout.addWidget(self._lbl_name)
        detail_layout.addWidget(self._lbl_game)
        detail_layout.addWidget(self._lbl_cal)
        detail_layout.addWidget(self._lbl_created)
        detail_layout.addWidget(self._lbl_modified)
        detail_layout.addWidget(desc_label)
        detail_layout.addWidget(self._txt_desc)

        right_layout.addWidget(self._detail_card)

        # Action buttons
        btn_grid = QHBoxLayout()
        btn_grid.setSpacing(8)

        self._btn_activate = QPushButton("✅   Activate Profile")
        self._btn_activate.setObjectName("btnStart")
        self._btn_activate.clicked.connect(self._on_activate)

        btn_grid.addWidget(self._btn_activate)
        btn_grid.addStretch()
        right_layout.addLayout(btn_grid)

        # CRUD row
        crud_row = QHBoxLayout()
        crud_row.setSpacing(8)

        self._btn_create    = QPushButton("＋  Create")
        self._btn_rename    = QPushButton("✏   Rename")
        self._btn_duplicate = QPushButton("⎘   Duplicate")
        self._btn_delete    = QPushButton("🗑  Delete")

        for btn in (self._btn_create, self._btn_rename, self._btn_duplicate, self._btn_delete):
            crud_row.addWidget(btn)
        crud_row.addStretch()

        self._btn_create.clicked.connect(self._on_create)
        self._btn_rename.clicked.connect(self._on_rename)
        self._btn_duplicate.clicked.connect(self._on_duplicate)
        self._btn_delete.clicked.connect(self._on_delete)

        right_layout.addLayout(crud_row)

        # Import / Export row
        io_row = QHBoxLayout()
        io_row.setSpacing(8)

        self._btn_import = QPushButton("📥   Import Profile")
        self._btn_export = QPushButton("📤   Export Profile")

        self._btn_import.clicked.connect(self._on_import)
        self._btn_export.clicked.connect(self._on_export)

        io_row.addWidget(self._btn_import)
        io_row.addWidget(self._btn_export)
        io_row.addStretch()
        right_layout.addLayout(io_row)

        # Close button
        close_row = QHBoxLayout()
        close_row.addStretch()
        btn_close = QPushButton("Close")
        btn_close.setObjectName("btnExit")
        btn_close.clicked.connect(self.accept)
        close_row.addWidget(btn_close)
        right_layout.addLayout(close_row)

        split.addWidget(right)
        split.setSizes([260, 640])
        root.addWidget(split, stretch=1)

        # Populate
        self._refresh_list()

    # ── List management ───────────────────────────────────────────────────────

    def _refresh_list(self) -> None:
        """Reload the profile list from the manager and restore selection."""
        current_sel = self._selected_name()
        self._list.blockSignals(True)
        self._list.clear()
        for name in self._manager.list_names():
            item = QListWidgetItem(name)
            if name == self._active_name:
                item.setText(f"✔  {name}")
                item.setForeground(Qt.green)
            self._list.addItem(item)
        self._list.blockSignals(False)

        # Restore selection
        target = current_sel or self._active_name
        for i in range(self._list.count()):
            raw = self._list.item(i).text().lstrip("✔  ").strip()
            if raw == target:
                self._list.setCurrentRow(i)
                break

    def _selected_name(self) -> Optional[str]:
        """Return the raw profile name of the currently selected list item."""
        item = self._list.currentItem()
        if item is None:
            return None
        return item.text().lstrip("✔  ").strip()

    def _on_selection_changed(self) -> None:
        name = self._selected_name()
        if name is None:
            return
        try:
            profile = self._manager._storage.load(name)
            if profile is None:
                return
            self._lbl_name.setText(profile.name)
            self._lbl_game.setText(f"🎮  {profile.metadata.game_name}" if profile.metadata.game_name else "")
            cal_txt = "✅  Calibrated" if profile.is_calibrated else "⚠️  Not Calibrated"
            self._lbl_cal.setText(cal_txt)
            created = profile.metadata.created_at[:10]
            modified = profile.metadata.modified_at[:10]
            self._lbl_created.setText(f"Created: {created}")
            self._lbl_modified.setText(f"Last modified: {modified}")
            self._txt_desc.setPlainText(profile.metadata.description or "No description.")
        except Exception as exc:
            logger.warning("ProfileDialog: error loading profile detail: %s", exc)

    # ── Actions ───────────────────────────────────────────────────────────────

    def _on_activate(self) -> None:
        name = self._selected_name()
        if name is None:
            return
        self._active_name = name
        self.profile_activated.emit(name)
        self._refresh_list()
        QMessageBox.information(self, "Profile Activated", f"Profile '{name}' is now active.")

    def _on_create(self) -> None:
        name, ok = QInputDialog.getText(self, "Create Profile", "Enter a name for the new profile:")
        if not ok or not name.strip():
            return
        try:
            game, _ = QInputDialog.getText(self, "Create Profile", "Optional game name (or leave blank):")
            self._manager.create(name.strip(), game_name=game.strip())
            self._refresh_list()
        except ValueError as exc:
            QMessageBox.warning(self, "Create Failed", str(exc))

    def _on_rename(self) -> None:
        old = self._selected_name()
        if old is None:
            return
        new_name, ok = QInputDialog.getText(self, "Rename Profile", f"New name for '{old}':", text=old)
        if not ok or not new_name.strip():
            return
        try:
            self._manager.rename(old, new_name.strip())
            if self._active_name == old:
                self._active_name = new_name.strip()
            self._refresh_list()
        except (ValueError, FileNotFoundError) as exc:
            QMessageBox.warning(self, "Rename Failed", str(exc))

    def _on_duplicate(self) -> None:
        source = self._selected_name()
        if source is None:
            return
        new_name, ok = QInputDialog.getText(self, "Duplicate Profile",
                                            f"Name for copy of '{source}':", text=f"{source} (Copy)")
        if not ok or not new_name.strip():
            return
        try:
            self._manager.duplicate(source, new_name.strip())
            self._refresh_list()
        except (ValueError, FileNotFoundError) as exc:
            QMessageBox.warning(self, "Duplicate Failed", str(exc))

    def _on_delete(self) -> None:
        name = self._selected_name()
        if name is None:
            return
        reply = QMessageBox.question(
            self, "Delete Profile",
            f"Permanently delete profile '{name}'?\nThis cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        try:
            self._manager.delete(name)
            if self._active_name == name:
                self._active_name = self._manager.active_name
            self._refresh_list()
        except ValueError as exc:
            QMessageBox.warning(self, "Delete Failed", str(exc))

    def _on_export(self) -> None:
        name = self._selected_name()
        if name is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Profile", f"{name}.json", "DriveByGesture Profile (*.json)"
        )
        if not path:
            return
        try:
            self._manager.export_profile(name, Path(path))
            QMessageBox.information(self, "Export Successful", f"Profile exported to:\n{path}")
        except Exception as exc:
            QMessageBox.critical(self, "Export Failed", str(exc))

    def _on_import(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Profile", "", "DriveByGesture Profile (*.json)"
        )
        if not path:
            return
        try:
            profile = self._manager.import_profile(Path(path))
            self._refresh_list()
            QMessageBox.information(self, "Import Successful",
                                    f"Profile '{profile.name}' imported successfully.")
        except ValueError as exc:
            QMessageBox.critical(self, "Import Failed", str(exc))
