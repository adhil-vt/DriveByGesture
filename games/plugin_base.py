"""
gesturedrive.games.plugin_base
================================
Re-exports IGamePlugin from core.interfaces.

Provides a clean import path for game plugin authors:
    from games.plugin_base import IGamePlugin
"""

from core.interfaces import IGamePlugin  # noqa: F401

__all__ = ["IGamePlugin"]
