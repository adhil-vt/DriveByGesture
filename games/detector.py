"""
gesturedrive.games.detector
============================
GameDetector: stateless service that scans running OS processes and
returns the first matching GamePreset from the registry.

Uses psutil for process enumeration. Gracefully handles all common
psutil exceptions (AccessDenied, NoSuchProcess, ZombieProcess).
Falls back to returning None if psutil is not installed.
"""

from __future__ import annotations

import logging
from typing import Optional

from games.registry import GamePreset, GameRegistry

logger = logging.getLogger(__name__)


class GameDetector:
    """
    Scans active OS processes and returns the first matching GamePreset.

    Parameters
    ----------
    registry:
        GameRegistry to use for process-name matching.
        Defaults to a registry loaded with BUILT_IN_PRESETS.

    Usage
    -----
        detector = GameDetector()
        preset = detector.detect_running()
        if preset:
            print(f"Detected: {preset.display_name}")
    """

    def __init__(self, registry: Optional[GameRegistry] = None) -> None:
        self._registry = registry or GameRegistry()

    def detect_running(self) -> Optional[GamePreset]:
        """
        Scan all active OS processes and return the first matching preset.

        Returns None if:
        - No supported game is running.
        - psutil is not installed.
        - Access is denied to process list.

        Never raises.
        """
        try:
            import psutil  # noqa: PLC0415
        except ImportError:
            logger.debug("GameDetector: psutil not available — detection disabled.")
            return None

        try:
            for proc in psutil.process_iter(["name"]):
                try:
                    proc_name = proc.info.get("name") or ""
                    if not proc_name:
                        continue
                    preset = self._registry.find_by_process(proc_name)
                    if preset is not None:
                        logger.debug(
                            "GameDetector: matched process '%s' → '%s'.",
                            proc_name,
                            preset.display_name,
                        )
                        return preset
                except (psutil.NoSuchProcess, psutil.ZombieProcess):
                    continue
                except psutil.AccessDenied:
                    continue
        except Exception as exc:
            logger.warning("GameDetector: unexpected error during scan: %s", exc)

        return None

    def is_game_running(self, game_id: str) -> bool:
        """
        Check if a specific game (by game_id) is currently running.

        Convenience wrapper over detect_running() for targeted checks.
        """
        preset = self.detect_running()
        return preset is not None and preset.game_id == game_id
