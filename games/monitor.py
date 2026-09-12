"""
gesturedrive.games.monitor
============================
GameMonitor: lightweight QThread that polls GameDetector at a fixed
interval and emits signals only when the detected game changes.

Uses Qt signals/slots for safe cross-thread UI communication —
identical pattern to PipelineWorker and PerformanceMonitor.
"""

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import QThread, Signal

from games.detector import GameDetector
from games.prefs import DetectionPrefs
from games.registry import GamePreset, GameRegistry

logger = logging.getLogger(__name__)


class GameMonitor(QThread):
    """
    Background thread that detects running supported games.

    Emits
    -----
    game_detected(GamePreset)
        Fired when a new game is detected (state change: none → game,
        or game_A → game_B).
    game_exited()
        Fired when the previously detected game is no longer running.
    status_tick(str)
        Fired each poll cycle with a human-readable status string,
        useful for the dashboard "Current Game" label.

    Parameters
    ----------
    prefs:
        DetectionPrefs controlling enable/disable and interval.
    registry:
        GameRegistry to pass to GameDetector.
    """

    game_detected = Signal(object)   # GamePreset
    game_exited   = Signal()
    status_tick   = Signal(str)      # human-readable game name or ""

    def __init__(
        self,
        prefs: Optional[DetectionPrefs] = None,
        registry: Optional[GameRegistry] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._prefs    = prefs    or DetectionPrefs()
        self._detector = GameDetector(registry or GameRegistry())
        self._running  = False
        self._current_preset: Optional[GamePreset] = None

    # ── Public API ────────────────────────────────────────────────────────────

    def stop(self) -> None:
        """Signal the poll loop to exit on the next iteration."""
        self._running = False

    @property
    def current_preset(self) -> Optional[GamePreset]:
        """The GamePreset most recently detected, or None."""
        return self._current_preset

    def set_interval(self, seconds: float) -> None:
        """Update the polling interval at runtime."""
        self._prefs.interval_seconds = max(1.0, seconds)

    # ── QThread loop ──────────────────────────────────────────────────────────

    def run(self) -> None:
        """Polling loop executed on the background thread."""
        self._running = True
        logger.info(
            "GameMonitor: started (interval=%.1fs, enabled=%s).",
            self._prefs.interval_seconds,
            self._prefs.enabled,
        )

        while self._running:
            if self._prefs.enabled:
                self._poll()

            # Interruptible sleep: check _running every 500ms
            interval_ms = int(self._prefs.interval_seconds * 1000)
            waited = 0
            while self._running and waited < interval_ms:
                self.msleep(500)
                waited += 500

        logger.info("GameMonitor: stopped.")

    def _poll(self) -> None:
        """Single detection cycle. Emits signals only on state changes."""
        try:
            detected = self._detector.detect_running()
        except Exception as exc:
            logger.warning("GameMonitor: poll error: %s", exc)
            return

        prev = self._current_preset

        if detected is not None:
            self.status_tick.emit(detected.display_name)
            if prev is None or prev.game_id != detected.game_id:
                # New game detected (or switched from another game)
                self._current_preset = detected
                logger.info("GameMonitor: detected '%s'.", detected.display_name)
                self.game_detected.emit(detected)
        else:
            self.status_tick.emit("")
            if prev is not None:
                # Game exited
                self._current_preset = None
                logger.info("GameMonitor: '%s' exited.", prev.display_name)
                self.game_exited.emit()
