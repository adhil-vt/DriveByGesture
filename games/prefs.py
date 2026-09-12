"""
gesturedrive.games.prefs
=========================
DetectionPrefs: user preferences for game detection behavior.

Stored in games/detection_prefs.json.
Controls auto-switch, prompt behavior, detection interval,
and per-game ignore/always-switch lists.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List, Optional

from core.resources import get_game_prefs_path, get_user_data_dir

logger = logging.getLogger(__name__)


def _get_default_prefs_path() -> Path:
    return get_game_prefs_path()


class DetectionPrefs:
    """
    Stores and persists user preferences for game detection and profile switching.

    JSON schema (all fields optional, defaults applied on load):
    {
        "enabled": true,
        "auto_switch": false,
        "prompt_before_switch": true,
        "interval_seconds": 5.0,
        "ignored_games": [],
        "always_switch_games": []
    }
    """

    def __init__(self, path: Optional[Path] = None) -> None:
        if path is not None:
            p = Path(path)
            if not p.is_absolute():
                p = get_user_data_dir() / p
            self._path = p
        else:
            self._path = _get_default_prefs_path()
        self.enabled: bool = True
        self.auto_switch: bool = False
        self.prompt_before_switch: bool = True
        self.interval_seconds: float = 5.0
        self.ignored_games: List[str] = []
        self.always_switch_games: List[str] = []
        self._load()

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load(self) -> None:
        """Load preferences from disk. Missing file is silently ignored."""
        if not self._path.exists():
            return
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.enabled              = bool(data.get("enabled", True))
            self.auto_switch          = bool(data.get("auto_switch", False))
            self.prompt_before_switch = bool(data.get("prompt_before_switch", True))
            self.interval_seconds     = float(data.get("interval_seconds", 5.0))
            self.ignored_games        = list(data.get("ignored_games", []))
            self.always_switch_games  = list(data.get("always_switch_games", []))
            logger.debug("DetectionPrefs: loaded from %s.", self._path)
        except (json.JSONDecodeError, OSError, ValueError) as exc:
            logger.warning("DetectionPrefs: could not load prefs (%s) — using defaults.", exc)

    def save(self) -> None:
        """Persist current preferences to disk."""
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "enabled":              self.enabled,
                "auto_switch":          self.auto_switch,
                "prompt_before_switch": self.prompt_before_switch,
                "interval_seconds":     self.interval_seconds,
                "ignored_games":        self.ignored_games,
                "always_switch_games":  self.always_switch_games,
            }
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            logger.debug("DetectionPrefs: saved to %s.", self._path)
        except OSError as exc:
            logger.warning("DetectionPrefs: could not save prefs: %s", exc)

    # ── Per-game preference helpers ───────────────────────────────────────────

    def is_ignored(self, game_id: str) -> bool:
        """Return True if the user has asked to never switch for this game."""
        return game_id in self.ignored_games

    def is_always_switch(self, game_id: str) -> bool:
        """Return True if the user has asked to always switch for this game."""
        return game_id in self.always_switch_games

    def set_ignored(self, game_id: str, ignored: bool = True) -> None:
        """Mark game_id as ignored (never prompt) and persist."""
        if ignored:
            if game_id not in self.ignored_games:
                self.ignored_games.append(game_id)
            # Remove from always_switch if previously set
            if game_id in self.always_switch_games:
                self.always_switch_games.remove(game_id)
        else:
            if game_id in self.ignored_games:
                self.ignored_games.remove(game_id)
        self.save()

    def set_always_switch(self, game_id: str, always: bool = True) -> None:
        """Mark game_id as always-switch (no prompt) and persist."""
        if always:
            if game_id not in self.always_switch_games:
                self.always_switch_games.append(game_id)
            # Remove from ignored if previously set
            if game_id in self.ignored_games:
                self.ignored_games.remove(game_id)
        else:
            if game_id in self.always_switch_games:
                self.always_switch_games.remove(game_id)
        self.save()

    def clear_game_pref(self, game_id: str) -> None:
        """Reset per-game preference for game_id (will prompt again)."""
        self.ignored_games = [g for g in self.ignored_games if g != game_id]
        self.always_switch_games = [g for g in self.always_switch_games if g != game_id]
        self.save()
