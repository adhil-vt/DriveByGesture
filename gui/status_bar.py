"""
gesturedrive.gui.status_bar
===========================
Bottom status bar displaying component connection indicators as modern pill-shaped chips with glowing status LEDs.
"""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel


class StatusBarWidget(QFrame):
    """
    Bottom bar widget containing modern pill-shaped status chips for all major backend subsystems.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("statusBar")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(12)

        # 1. Camera Status Chip
        self.ind_camera = self._create_chip("Camera", "Stopped", "#8f96a3")
        # 2. MediaPipe Tracking Status Chip
        self.ind_mediapipe = self._create_chip("MediaPipe", "Idle", "#8f96a3")
        # 3. Virtual Controller Status Chip
        self.ind_controller = self._create_chip("Controller", "Disconnected", "#8f96a3")
        # 4. Calibration Status Chip
        self.ind_calibration = self._create_chip("Calibration", "Default", "#ffb300")
        # 5. Game Detection Chip
        self.ind_game = self._create_chip("Game", "No game", "#5b616e")

        layout.addWidget(self.ind_camera)
        layout.addWidget(self.ind_mediapipe)
        layout.addWidget(self.ind_controller)
        layout.addWidget(self.ind_calibration)
        layout.addWidget(self.ind_game)
        layout.addStretch()

    def _create_chip(self, name: str, initial_status: str, color_hex: str) -> QLabel:
        lbl = QLabel(f"●  {name}: {initial_status}")
        lbl.setObjectName("statusChip")
        lbl.setStyleSheet(
            f"background-color: #11131a; color: {color_hex}; font-size: 12px; font-weight: 600; "
            f"padding: 6px 14px; border-radius: 14px; border: 1px solid #282c3c;"
        )
        return lbl

    def set_component_status(self, component: str, status_str: str, state: str = "auto") -> None:
        """
        Update status string and indicator color for a component.

        Colors:
        Green (#00e676): Connected, Running, Loaded
        Yellow (#ffb300): Waiting, Initializing, Safe Mode, Default
        Red (#ff1744): Disconnected, Error, Failed
        Gray (#8f96a3): Stopped, Idle
        """
        s_lower = status_str.lower()
        if state == "auto":
            if any(k in s_lower for k in ("connected", "running", "loaded", "ok")):
                color_hex = "#00e676"  # Green
            elif any(k in s_lower for k in ("waiting", "initializing", "safe", "default")):
                color_hex = "#ffb300"  # Yellow
            elif any(k in s_lower for k in ("disconnected", "error", "failed", "bad")):
                color_hex = "#ff1744"  # Red
            else:
                color_hex = "#8f96a3"  # Gray
        else:
            colors = {
                "good": "#00e676",
                "warn": "#ffb300",
                "bad": "#ff1744",
                "neutral": "#8f96a3",
                "active": "#00e5ff",
            }
            color_hex = colors.get(state, "#8f96a3")

        target_lbl = None
        if component.lower() == "camera":
            target_lbl = self.ind_camera
            name = "Camera"
        elif component.lower() in ("mediapipe", "tracking"):
            target_lbl = self.ind_mediapipe
            name = "MediaPipe"
        elif component.lower() in ("controller", "xbox"):
            target_lbl = self.ind_controller
            name = "Controller"
        elif component.lower() == "calibration":
            target_lbl = self.ind_calibration
            name = "Calibration"

        if target_lbl is not None:
            target_lbl.setText(f"●  {name}: {status_str}")
            target_lbl.setStyleSheet(
                f"background-color: #11131a; color: {color_hex}; font-size: 12px; font-weight: 600; "
                f"padding: 6px 14px; border-radius: 14px; border: 1px solid #282c3c;"
            )

    def update_game_chip(self, game_name: str) -> None:
        """
        Convenience method to update the game detection chip.
        Pass empty string to show idle state.
        """
        if game_name:
            self.ind_game.setText(f"●  Game: {game_name}")
            self.ind_game.setStyleSheet(
                "background-color: #11131a; color: #00e5ff; font-size: 12px; font-weight: 600; "
                "padding: 6px 14px; border-radius: 14px; border: 1px solid #282c3c;"
            )
        else:
            self.ind_game.setText("●  Game: No game")
            self.ind_game.setStyleSheet(
                "background-color: #11131a; color: #5b616e; font-size: 12px; font-weight: 600; "
                "padding: 6px 14px; border-radius: 14px; border: 1px solid #282c3c;"
            )
