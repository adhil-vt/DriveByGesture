"""
gesturedrive.gui.profile_widget
================================
ProfileSelectorWidget: Compact profile switcher embedded in the top bar.

Displays the active profile name and a QComboBox for quick switching.
Emits profile_switch_requested(name) signal — MainWindow handles the switch.
"""

from __future__ import annotations

import logging
from typing import List

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QFrame, QHBoxLayout, QLabel

logger = logging.getLogger(__name__)


class NoWheelComboBox(QComboBox):
    """QComboBox that ignores mouse wheel scroll events so page scrolling is not interrupted."""
    def wheelEvent(self, event) -> None:
        event.ignore()


class ProfileSelectorWidget(QFrame):
    """
    Compact inline widget: [ 👤 Profile: <name> | ▼ ComboBox ]

    Signals
    -------
    profile_switch_requested(str)
        Emitted when the user selects a different profile from the dropdown.
        The str is the requested profile name.
    """

    profile_switch_requested = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("pillBadge")
        self.setStyleSheet(
            "QFrame#pillBadge { background-color: #11131a; border: 1px solid #282c3c; "
            "border-radius: 14px; padding: 0px 4px; }"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 4, 2)
        layout.setSpacing(4)

        self._lbl_icon = QLabel("👤")
        self._lbl_icon.setStyleSheet("font-size: 14px; background: transparent; border: none;")

        self._lbl_prefix = QLabel("Profile:")
        self._lbl_prefix.setStyleSheet(
            "color: #5b616e; font-size: 11px; font-weight: 600; background: transparent; border: none;"
        )

        self._combo = NoWheelComboBox()
        self._combo.setFixedHeight(26)
        self._combo.setMinimumWidth(140)
        self._combo.setStyleSheet(
            "QComboBox { background: transparent; color: #ffb300; font-size: 12px; font-weight: 700; "
            "border: none; padding: 0 4px; }"
            "QComboBox::drop-down { border: none; width: 18px; }"
            "QComboBox::down-arrow { width: 10px; height: 10px; }"
            "QComboBox QAbstractItemView { background: #1a1d28; color: #ffffff; "
            "selection-background-color: #00e5ff22; border: 1px solid #282c3c; }"
        )
        self._combo.currentTextChanged.connect(self._on_combo_changed)

        layout.addWidget(self._lbl_icon)
        layout.addWidget(self._lbl_prefix)
        layout.addWidget(self._combo)

        self._updating = False

    # ── Public API ────────────────────────────────────────────────────────────

    def set_profiles(self, names: List[str]) -> None:
        """Populate combo box with profile names (does not emit signal)."""
        self._updating = True
        current = self._combo.currentText()
        self._combo.clear()
        self._combo.addItems(names)
        if current in names:
            self._combo.setCurrentText(current)
        self._updating = False

    def set_active_profile(self, name: str) -> None:
        """Update active profile display (does not emit signal)."""
        self._updating = True
        self._combo.setCurrentText(name)
        self._updating = False

    def current_profile_name(self) -> str:
        return self._combo.currentText()

    # ── Internal ─────────────────────────────────────────────────────────────

    def _on_combo_changed(self, name: str) -> None:
        if self._updating or not name:
            return
        logger.debug("ProfileSelectorWidget: user selected '%s'.", name)
        self.profile_switch_requested.emit(name)
