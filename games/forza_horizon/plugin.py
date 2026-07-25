"""
gesturedrive.games.forza_horizon.plugin
=========================================
ForzaHorizonPlugin: IGamePlugin implementation for Forza Horizon 5.

This is the concrete entry point that GamePluginLoader discovers and
registers. It delegates to ForzaInputProfile and ForzaSensitivityCurve
for all game-specific configuration.
"""

from __future__ import annotations

import logging

from core.interfaces import IGamePlugin
from core.models import InputProfile
from games.forza_horizon.input_profile import build_forza_input_profile

logger = logging.getLogger(__name__)

GAME_ID = "forza_horizon"
DISPLAY_NAME = "Forza Horizon 5"


class ForzaHorizonPlugin(IGamePlugin):
    """
    IGamePlugin for Forza Horizon 5.

    Provides the InputProfile (axis/button bindings, sensitivity curve)
    used by InputMapper when Forza Horizon is the active game.

    Registration (pyproject.toml)
    -----------------------------
    [project.entry-points."gesturedrive.games"]
    forza_horizon = "games.forza_horizon.plugin:ForzaHorizonPlugin"
    """

    @property
    def game_id(self) -> str:
        return GAME_ID

    @property
    def display_name(self) -> str:
        return DISPLAY_NAME

    def get_input_profile(self) -> InputProfile:
        """Return the Forza Horizon 5 InputProfile."""
        return build_forza_input_profile()

    def on_activate(self) -> None:
        """Called when Forza Horizon becomes the active game."""
        logger.info("ForzaHorizonPlugin: activated.")

    def on_deactivate(self) -> None:
        """Called when another game plugin takes over."""
        logger.info("ForzaHorizonPlugin: deactivated.")
