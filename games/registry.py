"""
gesturedrive.games.registry
============================
GamePreset dataclass and GameRegistry singleton.

GamePreset is a pure data object describing a supported game —
detection identifiers, suggested profile name, and recommended
steering settings.  It is separate from IGamePlugin (which handles
input mapping); this module is concerned only with detection & presets.

Adding a new game requires only adding one entry to BUILT_IN_PRESETS.
Zero other files need changing.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GamePreset:
    """
    Describes a supported driving game for detection and profile presets.

    Parameters
    ----------
    game_id:
        Unique machine-readable key, e.g. ``"beamng"``.
    display_name:
        Human-readable title shown in the UI.
    executables:
        List of process names to match (case-insensitive).
        Examples: ``["BeamNG.drive.exe", "BeamNG.drive"]``
    suggested_profile_name:
        Name to use when creating a profile for this game.
    description:
        Short one-line description shown in the profile dialog.
    default_steering:
        Recommended steering settings merged into DriveProfile.steering
        when the preset profile is created.
    """
    game_id: str
    display_name: str
    executables: List[str]
    suggested_profile_name: str
    description: str = ""
    default_steering: Dict = field(default_factory=dict)

    def matches_process(self, process_name: str) -> bool:
        """Return True if process_name matches any registered executable."""
        name_lower = process_name.lower()
        return any(exe.lower() == name_lower for exe in self.executables)


# ── Built-in game registry entries ────────────────────────────────────────────

BUILT_IN_PRESETS: List[GamePreset] = [
    GamePreset(
        game_id="forza_horizon_5",
        display_name="Forza Horizon 5",
        executables=["ForzaHorizon5.exe", "forza_horizon5.exe"],
        suggested_profile_name="Forza Horizon 5",
        description="Open-world arcade racing by Playground Games.",
        default_steering={
            "max_steering_angle": 30.0,
            "steering_deadzone": 0.04,
            "steering_sensitivity": 1.1,
            "steering_smoothing_alpha": 0.18,
            "steering_curve_exponent": 2.5,
            "steering_inversion": False,
        },
    ),
    GamePreset(
        game_id="euro_truck_simulator_2",
        display_name="Euro Truck Simulator 2",
        executables=["eurotrucks2.exe", "EuroTrucks2.exe"],
        suggested_profile_name="Euro Truck Simulator 2",
        description="European long-haul trucking simulation by SCS Software.",
        default_steering={
            "max_steering_angle": 25.0,
            "steering_deadzone": 0.06,
            "steering_sensitivity": 0.85,
            "steering_smoothing_alpha": 0.12,
            "steering_curve_exponent": 3.0,
            "steering_inversion": False,
        },
    ),
    GamePreset(
        game_id="american_truck_simulator",
        display_name="American Truck Simulator",
        executables=["amtrucks.exe", "AmTrucks.exe"],
        suggested_profile_name="American Truck Simulator",
        description="American long-haul trucking simulation by SCS Software.",
        default_steering={
            "max_steering_angle": 25.0,
            "steering_deadzone": 0.06,
            "steering_sensitivity": 0.85,
            "steering_smoothing_alpha": 0.12,
            "steering_curve_exponent": 3.0,
            "steering_inversion": False,
        },
    ),
    GamePreset(
        game_id="assetto_corsa",
        display_name="Assetto Corsa",
        executables=["acs.exe", "AssettoCorsa.exe"],
        suggested_profile_name="Assetto Corsa",
        description="Realistic motorsport simulation by Kunos Simulazioni.",
        default_steering={
            "max_steering_angle": 35.0,
            "steering_deadzone": 0.03,
            "steering_sensitivity": 1.2,
            "steering_smoothing_alpha": 0.10,
            "steering_curve_exponent": 2.2,
            "steering_inversion": False,
        },
    ),
    GamePreset(
        game_id="beamng_drive",
        display_name="BeamNG.drive",
        executables=["BeamNG.drive.exe", "beamng.drive.exe", "BeamNG.exe"],
        suggested_profile_name="BeamNG.drive",
        description="Realistic soft-body vehicle simulator by BeamNG GmbH.",
        default_steering={
            "max_steering_angle": 32.0,
            "steering_deadzone": 0.04,
            "steering_sensitivity": 1.0,
            "steering_smoothing_alpha": 0.14,
            "steering_curve_exponent": 2.8,
            "steering_inversion": False,
        },
    ),
]


class GameRegistry:
    """
    Central registry of supported games.

    Holds all GamePreset objects and provides lookup by game_id or
    process name.  New games are added by extending BUILT_IN_PRESETS —
    no code changes needed elsewhere.

    Usage
    -----
        registry = GameRegistry()
        preset = registry.find_by_process("BeamNG.drive.exe")
    """

    def __init__(self, presets: Optional[List[GamePreset]] = None) -> None:
        self._presets: Dict[str, GamePreset] = {}
        for p in (presets or BUILT_IN_PRESETS):
            self._presets[p.game_id] = p
        logger.debug("GameRegistry: loaded %d preset(s).", len(self._presets))

    # ── Lookup ────────────────────────────────────────────────────────────────

    def find_by_id(self, game_id: str) -> Optional[GamePreset]:
        """Return the preset for game_id, or None."""
        return self._presets.get(game_id)

    def find_by_process(self, process_name: str) -> Optional[GamePreset]:
        """Return the first preset whose executable list matches process_name."""
        for preset in self._presets.values():
            if preset.matches_process(process_name):
                return preset
        return None

    def all_presets(self) -> List[GamePreset]:
        """Return all registered presets sorted by display name."""
        return sorted(self._presets.values(), key=lambda p: p.display_name)

    def game_ids(self) -> List[str]:
        """Return all registered game IDs."""
        return list(self._presets.keys())

    # ── Registration (for plugins / future extensibility) ─────────────────────

    def register(self, preset: GamePreset) -> None:
        """Add a new preset at runtime (e.g., from a plugin)."""
        if preset.game_id in self._presets:
            logger.warning("GameRegistry: duplicate game_id '%s' — overwriting.", preset.game_id)
        self._presets[preset.game_id] = preset
        logger.info("GameRegistry: registered '%s'.", preset.display_name)
