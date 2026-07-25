"""
gesturedrive.config.loader
============================
ConfigLoader: reads, merges, and validates TOML configuration files.

Merge strategy
--------------
1. Start with defaults (AppConfig with all defaults).
2. Overlay config/default.toml (shipped with the application).
3. Overlay config/user/<name>.toml (user overrides, if present).
4. Return the merged AppConfig.

Implementation note
-------------------
Uses ``tomllib`` (stdlib in Python 3.11+) or ``tomli`` as a backport
for Python 3.9–3.10.  The import is guarded with a try/except.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from config.schema import AppConfig
from core.exceptions import ConfigError

logger = logging.getLogger(__name__)

try:
    import tomllib                  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib     # type: ignore[no-redef]  # backport
    except ImportError:
        tomllib = None              # type: ignore[assignment]


class ConfigLoader:
    """
    Reads TOML configuration files and constructs a merged AppConfig.

    Parameters
    ----------
    default_config_path:
        Path to the application's shipped ``config/default.toml``.
    user_config_path:
        Path to the user's override TOML file. May not exist.

    Raises
    ------
    ConfigError
        If a TOML file exists but cannot be parsed (malformed syntax or
        unknown top-level section).
    ImportError
        On Python < 3.11 if neither ``tomllib`` nor ``tomli`` is installed.
    """

    def __init__(
        self,
        default_config_path: Path,
        user_config_path: Optional[Path] = None,
    ) -> None:
        self._default_path = default_config_path
        self._user_path = user_config_path

    def load(self) -> AppConfig:
        """
        Read and merge all config sources into a single AppConfig.

        Returns
        -------
        AppConfig
            Fully resolved configuration with user overrides applied.

        Raises
        ------
        ConfigError
            If any config file is malformed.
        """
        raise NotImplementedError

    def save_user_config(self, config: AppConfig) -> None:
        """
        Serialize ``config`` back to the user config TOML file.

        Called by ConfigManager when the user changes settings via the UI.
        """
        raise NotImplementedError

    # ── Private helpers ───────────────────────────────────────────────────────

    def _read_toml(self, path: Path) -> dict:
        """
        Read a TOML file and return its contents as a dict.

        Raises
        ------
        ConfigError
            On parse failure.
        """
        raise NotImplementedError

    @staticmethod
    def _merge(base: AppConfig, overrides: dict) -> AppConfig:
        """
        Apply a nested dict of overrides onto a base AppConfig.

        Unknown keys in ``overrides`` are logged at WARNING and ignored.
        """
        raise NotImplementedError
