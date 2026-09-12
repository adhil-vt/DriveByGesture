"""
gesturedrive.gui.game_status_widget
=====================================
GameStatusWidget: compact dashboard card showing the currently
detected game name and its status (detected / idle).

Designed to sit at the top of the TelemetryPanel, above the
steering wheel, providing a clear "Current Game" indicator.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout


class GameStatusWidget(QFrame):
    """
    Compact card widget showing the currently detected game.

    When a game is detected:
        🎮 BeamNG.drive          [green dot + name]
        Auto-detect active

    When idle:
        🎮 No game detected     [muted]
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("statusCard")
        self.setMaximumHeight(72)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 10, 14, 10)
        outer.setSpacing(4)

        # Section label
        section_lbl = QLabel("CURRENT GAME")
        section_lbl.setObjectName("sectionTitle")

        # Status row
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        self._icon_lbl = QLabel("🎮")
        self._icon_lbl.setStyleSheet("font-size: 18px; background: transparent;")
        self._icon_lbl.setFixedWidth(26)

        self._name_lbl = QLabel("No game detected")
        self._name_lbl.setStyleSheet(
            "color: #5b616e; font-size: 13px; font-weight: 700; background: transparent;"
        )

        self._dot_lbl = QLabel("●")
        self._dot_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._dot_lbl.setStyleSheet(
            "color: #5b616e; font-size: 10px; background: transparent;"
        )

        row.addWidget(self._icon_lbl)
        row.addWidget(self._name_lbl, stretch=1)
        row.addWidget(self._dot_lbl)

        outer.addWidget(section_lbl)
        outer.addLayout(row)

    # ── Public API ────────────────────────────────────────────────────────────

    def set_game(self, game_name: str, game_id: Optional[str] = None) -> None:
        """Update widget to show a detected game."""
        self._name_lbl.setText(game_name)
        self._name_lbl.setStyleSheet(
            "color: #00e5ff; font-size: 13px; font-weight: 700; background: transparent;"
        )
        self._dot_lbl.setStyleSheet(
            "color: #00e676; font-size: 10px; background: transparent;"
        )

    def set_idle(self) -> None:
        """Update widget to idle (no game detected) state."""
        self._name_lbl.setText("No game detected")
        self._name_lbl.setStyleSheet(
            "color: #5b616e; font-size: 13px; font-weight: 700; background: transparent;"
        )
        self._dot_lbl.setStyleSheet(
            "color: #5b616e; font-size: 10px; background: transparent;"
        )
