"""
gesturedrive.gui.logger
======================
Logging architecture interface for PySide6 GUI integration.
"""

from __future__ import annotations

import logging
from PySide6.QtCore import QObject, Signal


class LogSignalEmitter(QObject):
    """Qt Signal Emitter for log messages."""
    log_emitted = Signal(str, str)  # (level, message)


class GUILogHandler(logging.Handler):
    """
    Custom logging handler that intercepts Python standard log messages
    and emits Qt signals for future GUI log windows and status displays.
    """

    def __init__(self, level: int = logging.INFO) -> None:
        super().__init__(level)
        self.emitter = LogSignalEmitter()
        self.setFormatter(
            logging.Formatter("[%(asctime)s] [%(levelname)s] %(name)s: %(message)s", "%H:%M:%S")
        )

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            self.emitter.log_emitted.emit(record.levelname, msg)
        except Exception:
            self.handleError(record)
