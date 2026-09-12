"""
gesturedrive.desktop.manager
=============================
ModeManager: Master orchestrator for application operating modes.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, List, Optional

from core.resources import get_active_mode_path
from desktop.enums import AppMode

logger = logging.getLogger(__name__)


def _get_active_mode_state_file() -> Path:
    return get_active_mode_path()


class ModeManager:
    """
    Manages active application mode (DRIVING vs DESKTOP) and fires callbacks on change.

    Parameters
    ----------
    initial_mode: AppMode
        Default operating mode at startup.
    on_mode_changed: Optional[Callable[[AppMode], None]]
        Callback fired whenever mode switches.
    """

    def __init__(
        self,
        initial_mode: AppMode = AppMode.DRIVING,
        on_mode_changed: Optional[Callable[[AppMode], None]] = None,
    ) -> None:
        self._on_mode_changed = on_mode_changed
        self._mode: AppMode = self._restore_saved_mode() or initial_mode

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def active_mode(self) -> AppMode:
        """The currently active AppMode."""
        return self._mode

    @property
    def mode_name(self) -> str:
        """Human readable mode name ('Driving Mode' vs 'Desktop Mode')."""
        return "Driving Mode" if self._mode == AppMode.DRIVING else "Desktop Mode"

    @property
    def is_desktop_active(self) -> bool:
        """True if DESKTOP mode is currently active."""
        return self._mode == AppMode.DESKTOP

    @property
    def is_driving_active(self) -> bool:
        """True if DRIVING mode is currently active."""
        return self._mode == AppMode.DRIVING

    # ── Actions ───────────────────────────────────────────────────────────────

    def set_mode(self, mode: AppMode | str) -> AppMode:
        """
        Switch active operating mode live without application restarts.
        """
        target = AppMode.from_str(mode) if isinstance(mode, str) else mode
        if self._mode == target:
            return self._mode

        old_mode = self._mode
        self._mode = target
        self._persist_mode(target)
        logger.info("ModeManager: switched mode '%s' → '%s'.", old_mode.name, target.name)

        if self._on_mode_changed:
            try:
                self._on_mode_changed(target)
            except Exception as exc:
                logger.error("ModeManager: callback error on mode change: %s", exc)

        return self._mode

    def toggle_mode(self) -> AppMode:
        """Toggle between DRIVING and DESKTOP modes."""
        new_mode = AppMode.DESKTOP if self._mode == AppMode.DRIVING else AppMode.DRIVING
        return self.set_mode(new_mode)

    # ── Internal Persistence ──────────────────────────────────────────────────

    def _persist_mode(self, mode: AppMode) -> None:
        try:
            state_file = _get_active_mode_state_file()
            state_file.parent.mkdir(parents=True, exist_ok=True)
            state_file.write_text(mode.value, encoding="utf-8")
        except OSError as exc:
            logger.warning("ModeManager: failed to persist active mode: %s", exc)

    def _restore_saved_mode(self) -> Optional[AppMode]:
        try:
            state_file = _get_active_mode_state_file()
            if state_file.exists():
                txt = state_file.read_text(encoding="utf-8").strip()
                return AppMode.from_str(txt)
        except OSError:
            pass
        return None
