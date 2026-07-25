"""
gesturedrive.controller.null_controller
==========================================
NullController: a no-op IVirtualController for testing and safe mode.

Design
------
- Accepts all controller inputs silently and discards them.
- Never raises ControllerError.
- Always reports ``is_connected = True``.
- Optional logging mode: prints received inputs at DEBUG level.
  Useful for verifying the pipeline produces correct outputs without
  requiring ViGEmBus to be installed.

Usage
-----
- In unit / integration tests: inject NullController to avoid requiring
  the ViGEmBus driver.
- In production safe mode: if XboxController.connect() raises ControllerError,
  the Application falls back to NullController and publishes an ErrorEvent.
"""

from __future__ import annotations

import logging

from core.interfaces import IVirtualController
from core.models import ControllerInput

logger = logging.getLogger(__name__)


class NullController(IVirtualController):
    """
    Silent no-op virtual controller.

    Parameters
    ----------
    log_inputs:
        If True, log every received ControllerInput at DEBUG level.
        Defaults to False.
    """

    def __init__(self, log_inputs: bool = False) -> None:
        self._log_inputs = log_inputs
        self._connected = False

    def connect(self) -> None:
        """Mark as connected (no hardware interaction)."""
        self._connected = True
        logger.info("NullController: connected (no-op).")

    def apply(self, input_snapshot: ControllerInput) -> None:
        """Silently discard the input snapshot."""
        if self._log_inputs:
            logger.debug("NullController.apply: %s", input_snapshot)

    def reset(self) -> None:
        """No-op: there are no physical axes to reset."""
        logger.debug("NullController.reset (no-op).")

    def disconnect(self) -> None:
        """Mark as disconnected."""
        self._connected = False
        logger.info("NullController: disconnected (no-op).")

    @property
    def is_connected(self) -> bool:
        return self._connected
