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
from typing import Any, Optional

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
        config = AppConfig()
        if self._default_path.exists():
            config = self._merge(config, self._read_toml(self._default_path))
        if self._user_path and self._user_path.exists():
            config = self._merge(config, self._read_toml(self._user_path))
        return config

    def save_user_config(self, config: AppConfig) -> None:
        """
        Serialize ``config`` back to the user config TOML file.

        Called by ConfigManager when the user changes settings via the UI.
        """
        if self._user_path is None:
            raise ConfigError("No user config path was configured.")

        self._user_path.parent.mkdir(parents=True, exist_ok=True)
        data = config.to_dict()
        with self._user_path.open("w", encoding="utf-8") as fh:
            fh.write(self._to_toml(data))

    # ── Private helpers ───────────────────────────────────────────────────────

    def _read_toml(self, path: Path) -> dict:
        """
        Read a TOML file and return its contents as a dict.

        Raises
        ------
        ConfigError
            On parse failure.
        """
        if tomllib is None:
            raise ImportError("tomllib/tomli is required to read configuration files.")
        try:
            with path.open("rb") as fh:
                data = tomllib.load(fh)
        except (OSError, ValueError, tomllib.TOMLDecodeError) as exc:  # type: ignore[attr-defined]
            raise ConfigError(f"Failed to read config file '{path}': {exc}") from exc
        if not isinstance(data, dict):
            raise ConfigError(f"Config file '{path}' did not contain a TOML table.")
        return data

    @staticmethod
    def _merge(base: AppConfig, overrides: dict) -> AppConfig:
        """
        Apply a nested dict of overrides onto a base AppConfig.

        Unknown keys in ``overrides`` are logged at WARNING and ignored.
        """
        payload = base.to_dict()

        for section, values in overrides.items():
            if section not in payload:
                logger.warning("ConfigLoader: ignoring unknown config section '%s'.", section)
                continue
            if not isinstance(values, dict):
                logger.warning("ConfigLoader: ignoring non-table config section '%s'.", section)
                continue

            current = payload.get(section, {})
            if isinstance(current, dict):
                merged = dict(current)
                for key, value in values.items():
                    if isinstance(value, dict) and isinstance(merged.get(key), dict):
                        nested = dict(merged.get(key, {}))
                        nested.update(value)
                        merged[key] = nested
                    else:
                        merged[key] = value
                payload[section] = merged

        return AppConfig.from_dict(payload)

    @staticmethod
    def _to_toml(data: dict) -> str:
        lines: list[str] = []

        def emit_table(name: str, table: dict) -> None:
            scalar_items: list[tuple[str, Any]] = []
            nested_items: list[tuple[str, dict]] = []
            for key, value in table.items():
                if isinstance(value, dict):
                    nested_items.append((key, value))
                else:
                    scalar_items.append((key, value))

            if name:
                lines.append(f"[{name}]")

            for key, value in scalar_items:
                lines.append(f"{key} = {ConfigLoader._toml_value(value)}")

            for key, value in nested_items:
                if lines and lines[-1] != "":
                    lines.append("")
                child_name = f"{name}.{key}" if name else key
                emit_table(child_name, value)

        top_level = {k: v for k, v in data.items() if isinstance(v, dict)}
        for key, value in data.items():
            if not isinstance(value, dict):
                lines.append(f"{key} = {ConfigLoader._toml_value(value)}")
        if data:
            for key, value in top_level.items():
                if lines and lines[-1] != "":
                    lines.append("")
                emit_table(key, value)
        return "\n".join(lines) + "\n"

    @staticmethod
    def _toml_value(value: Any) -> str:
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, int) and not isinstance(value, bool):
            return str(value)
        if isinstance(value, float):
            return repr(value)
        if isinstance(value, str):
            escaped = value.replace("\\", "\\\\").replace('"', '\\"')
            return f'"{escaped}"'
        if isinstance(value, dict):
            items = ", ".join(f"{k} = {ConfigLoader._toml_value(v)}" for k, v in value.items())
            return f"{{ {items} }}"
        if value is None:
            return '""'
        return ConfigLoader._toml_value(str(value))
