"""
gesturedrive.config.manager
=============================
ConfigManager: runtime access layer for application configuration.

Responsibilities
----------------
- Provides a typed ``get()`` API for reading config values at runtime.
- Watches the user config file for changes via ``watchdog`` (hot-reload).
- On change: validates, merges, and publishes ``ConfigChangedEvent``.
- Provides ``set()`` to update a key at runtime and persist to user TOML.

Design
------
- ConfigManager depends on ConfigLoader (injected).
- All services that need config access receive ConfigManager at construction.
- Services subscribe to ``ConfigChangedEvent`` to react to changes without
  being polled.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

from config.loader import ConfigLoader
from config.schema import AppConfig
from core.event_bus import EventBus
from core.events import ConfigChangedEvent

logger = logging.getLogger(__name__)

_SOURCE_ID = "config.manager"


class ConfigManager:
    """
    Central runtime configuration store with hot-reload support.

    Parameters
    ----------
    config:
        The initial AppConfig loaded at startup.
    loader:
        ConfigLoader used for saving user overrides.
    event_bus:
        The application-wide EventBus. ConfigChangedEvent is published here.

    Hot-reload
    ----------
    When ``start_watching()`` is called, a watchdog observer monitors the
    user config file. On change, the file is reloaded, validated, merged,
    and ``ConfigChangedEvent`` is published for each changed value.
    """

    def __init__(
        self,
        config: AppConfig,
        loader: ConfigLoader,
        event_bus: EventBus,
    ) -> None:
        self._config = config
        self._loader = loader
        self._bus = event_bus
        self._observer = None  # watchdog.observers.Observer — set in start_watching()

    # ── Read access ───────────────────────────────────────────────────────────

    @property
    def config(self) -> AppConfig:
        """The current active AppConfig. Read-only; use set() to mutate."""
        return self._config

    def get(self, section: str, key: str, default: Any = None) -> Any:
        """
        Read a config value by section and key.

        Parameters
        ----------
        section:
            The top-level config section name, e.g. ``"camera"``.
        key:
            The field name within the section, e.g. ``"fps"``.
        default:
            Returned if the section or key does not exist.

        Returns
        -------
        Any
            The resolved config value.
        """
        raise NotImplementedError

    # ── Write access ──────────────────────────────────────────────────────────

    def set(self, section: str, key: str, value: Any) -> None:
        """
        Update a config value at runtime and persist it to the user TOML.

        Publishes ``ConfigChangedEvent`` on the EventBus.

        Raises
        ------
        ConfigError
            If the section or key does not exist in the schema.
        """
        raise NotImplementedError

    # ── Hot-reload ────────────────────────────────────────────────────────────

    def start_watching(self) -> None:
        """
        Start the watchdog file observer on the user config file.

        No-op if the user config path is not set or does not exist yet.
        """
        raise NotImplementedError

    def stop_watching(self) -> None:
        """Stop the file observer and clean up the watchdog thread."""
        raise NotImplementedError

    def flush(self) -> None:
        """
        Persist the current in-memory config to the user TOML file.

        Called during application shutdown to ensure any runtime changes
        survive the session.
        """
        raise NotImplementedError
