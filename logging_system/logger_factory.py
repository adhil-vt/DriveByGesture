"""
gesturedrive.logging_system.logger_factory
============================================
LoggerFactory: creates pre-configured loggers for all GestureDrive modules.

All loggers are children of the root ``gesturedrive`` logger, which is
configured once during application startup.

Usage
-----
    from logging_system.logger_factory import LoggerFactory

    # In any module:
    logger = LoggerFactory.get(__name__)
"""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path
from typing import Optional


class LoggerFactory:
    """
    Factory for named loggers within the ``gesturedrive`` hierarchy.

    Class-level methods; no instance required.

    Configuration
    -------------
    Call ``LoggerFactory.configure()`` once at application startup with
    the resolved LoggingConfig. All subsequent ``get()`` calls return
    loggers that inherit the configured handlers and level.
    """

    _configured: bool = False

    @classmethod
    def configure(
        cls,
        level: str = "INFO",
        log_file: Optional[Path] = None,
        max_bytes: int = 10_485_760,
        backup_count: int = 5,
        json_format: bool = False,
    ) -> None:
        """
        Configure the root ``gesturedrive`` logger.

        Must be called once before any module calls ``get()``.
        Safe to call multiple times (re-configures handlers).

        Parameters
        ----------
        level:
            Root log level: ``"DEBUG"``, ``"INFO"``, ``"WARNING"``, etc.
        log_file:
            Path to the rotating log file. If None, file logging is disabled.
        max_bytes:
            Maximum log file size before rotation.
        backup_count:
            Number of rotated log file backups to keep.
        json_format:
            If True, use JsonFormatter for the file handler.
        """
        raise NotImplementedError

    @classmethod
    def get(cls, name: str) -> logging.Logger:
        """
        Return a named child logger under the ``gesturedrive`` hierarchy.

        Parameters
        ----------
        name:
            Typically ``__name__`` of the calling module.
            e.g. ``"gesture.builtin.steering"`` → child of root logger.

        Returns
        -------
        logging.Logger
            A configured logger instance.
        """
        return logging.getLogger(name)

    @classmethod
    def shutdown(cls) -> None:
        """Flush and close all logging handlers gracefully."""
        logging.shutdown()
