"""
gesturedrive.gui.mode_widget
=============================
ModeSelectorWidget: Compact operating mode selector embedded in the top bar.

Displays active mode (Driving Mode / Desktop Mode) and a QComboBox for quick live switching.
Emits mode_switch_requested(str) signal — MainWindow handles mode state.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QFrame, QHBoxLayout, QLabel

logger = logging.getLogger(__name__)


class NoWheelComboBox(QComboBox):
    """QComboBox that ignores mouse wheel scroll events so page scrolling is not interrupted."""
    def wheelEvent(self, event) -> None:
        event.ignore()


class ModeSelectorWidget(QFrame):
    """
    Compact inline widget: [ 🎮 Mode: <Driving | Desktop> | ▼ ComboBox ]

    Signals
    -------
    mode_switch_requested(str)
        Emitted when the user selects a mode ("driving" or "desktop").
    """

    mode_switch_requested = Signal(str)

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

        self._lbl_icon = QLabel("🎮")
        self._lbl_icon.setStyleSheet("font-size: 14px; background: transparent; border: none;")

        self._lbl_prefix = QLabel("Mode:")
        self._lbl_prefix.setStyleSheet(
            "color: #5b616e; font-size: 11px; font-weight: 600; background: transparent; border: none;"
        )

        self._combo = NoWheelComboBox()
        self._combo.setFixedHeight(26)
        self._combo.setMinimumWidth(130)
        self._combo.setStyleSheet(
            "QComboBox { background: transparent; color: #00e5ff; font-size: 12px; font-weight: 700; "
            "border: none; padding: 0 4px; }"
            "QComboBox::drop-down { border: none; width: 18px; }"
            "QComboBox::down-arrow { width: 10px; height: 10px; }"
            "QComboBox QAbstractItemView { background: #1a1d28; color: #ffffff; "
            "selection-background-color: #00e5ff22; border: 1px solid #282c3c; }"
        )

        self._combo.addItem("🚗 Driving", "driving")
        self._combo.addItem("🖥️ Desktop", "desktop")

        self._combo.currentIndexChanged.connect(self._on_combo_changed)

        layout.addWidget(self._lbl_icon)
        layout.addWidget(self._lbl_prefix)
        layout.addWidget(self._combo)

        self._updating = False

    def set_active_mode(self, mode_str: str) -> None:
        """Update active mode display without emitting signal."""
        self._updating = True
        s = str(mode_str).lower().strip()
        idx = 1 if "desktop" in s else 0
        self._combo.setCurrentIndex(idx)
        self._lbl_icon.setText("🖥️" if idx == 1 else "🚗")
        self._updating = False

    def current_mode_str(self) -> str:
        return self._combo.currentData() or "driving"

    def _on_combo_changed(self, index: int) -> None:
        if self._updating:
            return
        data = self._combo.itemData(index) or "driving"
        self._lbl_icon.setText("🖥️" if data == "desktop" else "🚗")
        logger.debug("ModeSelectorWidget: user selected mode '%s'.", data)
        self.mode_switch_requested.emit(data)
