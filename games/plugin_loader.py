"""
gesturedrive.games.plugin_loader
===================================
GamePluginLoader: discovers and instantiates all registered IGamePlugin
implementations at application startup.

Discovery strategy (in priority order)
---------------------------------------
1. Entry points (external packages):
   ``importlib.metadata.entry_points(group="gesturedrive.games")``
   Allows third-party game plugins distributed as separate PyPI packages.

2. Local sub-packages:
   Scan ``games/`` for any subpackage containing a ``plugin.py`` with a
   non-abstract IGamePlugin subclass.
   Always loads the first-party ``games.forza_horizon`` plugin.

Error handling
--------------
A plugin that raises any exception during import or instantiation is
skipped and a PluginError is logged at WARNING level. The loader never
allows a bad plugin to prevent the application from starting.
"""

from __future__ import annotations

import importlib
import importlib.metadata
import logging
from typing import Dict, List, Optional

from core.exceptions import PluginError
from core.interfaces import IGamePlugin

logger = logging.getLogger(__name__)


class GamePluginLoader:
    """
    Discovers, loads, and manages the lifecycle of IGamePlugin instances.

    Attributes
    ----------
    _plugins:
        Dict mapping ``game_id`` → IGamePlugin instance.
    _active:
        The currently active IGamePlugin, or None.

    Usage
    -----
        loader = GamePluginLoader()
        loader.discover()
        loader.activate("forza_horizon")
        plugin = loader.active_plugin
    """

    def __init__(self) -> None:
        self._plugins: Dict[str, IGamePlugin] = {}
        self._active: Optional[IGamePlugin] = None

    def discover(self) -> None:
        """
        Scan for and instantiate all available game plugins.

        Logs the names of all loaded plugins at INFO level.
        Logs and skips any plugin that fails to load.
        """
        self._plugins.clear()
        self._load_from_entry_points()
        self._load_local_plugins()
        logger.info(
            "GamePluginLoader: discovered %d plugin(s): %s",
            len(self._plugins),
            list(self._plugins.keys()),
        )

    def activate(self, game_id: str) -> None:
        """
        Set the plugin for ``game_id`` as the active plugin.

        Calls ``on_deactivate()`` on the previous plugin and ``on_activate()``
        on the new one.

        Raises
        ------
        PluginError
            If ``game_id`` is not in the discovered plugin registry.
        """
        raise NotImplementedError

    @property
    def active_plugin(self) -> Optional[IGamePlugin]:
        """The currently active IGamePlugin, or None if none is selected."""
        return self._active

    def all_plugins(self) -> List[IGamePlugin]:
        """Return all discovered plugins as a list."""
        return list(self._plugins.values())

    # ── Private discovery helpers ─────────────────────────────────────────────

    def _load_from_entry_points(self) -> None:
        """Load plugins registered via pyproject.toml entry points."""
        raise NotImplementedError

    def _load_local_plugins(self) -> None:
        """Scan games/ subdirectories for local plugin.py modules."""
        raise NotImplementedError

    def _register(self, plugin: IGamePlugin) -> None:
        """Add a validated plugin to the registry."""
        if plugin.game_id in self._plugins:
            logger.warning(
                "Duplicate game_id '%s' from %s — skipping.",
                plugin.game_id,
                type(plugin).__name__,
            )
            return
        self._plugins[plugin.game_id] = plugin
        logger.debug("Registered game plugin: '%s'.", plugin.game_id)
