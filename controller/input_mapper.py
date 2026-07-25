"""
gesturedrive.controller.input_mapper
=======================================
InputMapper: translates GestureResultSet → ControllerInput.

Responsibility
--------------
InputMapper is the bridge between the gesture domain and the controller domain.
It applies, in order:
  1. CalibrationProfile offsets (zero the neutral position).
  2. Game-specific InputProfile bindings (which gesture drives which axis).
  3. Game-specific sensitivity curve (e.g., Forza's non-linear steering curve).
  4. Deadzone clamping per binding.
  5. Final [-1.0, 1.0] / [0.0, 1.0] range clamping.

Design
------
- Pure transformation: no side effects, no I/O.
- Receives CalibrationProfile and InputProfile via constructor injection.
- Both can be replaced at runtime via setters (profile switch, recalibration).
- The ControllerService owns the InputMapper and calls map() on each gesture event.
"""

from __future__ import annotations

import logging
import math
from typing import Optional

from core.interfaces import IInputMapper
from core.models import (
    AxisValues,
    ButtonState,
    CalibrationProfile,
    ControllerInput,
    GestureResultSet,
    InputProfile,
)

logger = logging.getLogger(__name__)


class InputMapper(IInputMapper):
    """
    Translates a GestureResultSet into a ControllerInput snapshot.

    Parameters
    ----------
    calibration:
        Per-user calibration baselines. May be None before first calibration
        (mapper falls back to uncalibrated raw values).
    input_profile:
        Game-specific axis/button bindings and sensitivity curve config.
    """

    def __init__(
        self,
        calibration: Optional[CalibrationProfile],
        input_profile: InputProfile,
    ) -> None:
        self._calibration = calibration
        self._input_profile = input_profile

    # ── Runtime replacements ──────────────────────────────────────────────────

    def set_calibration(self, calibration: Optional[CalibrationProfile]) -> None:
        """Replace the active CalibrationProfile (e.g., after recalibration)."""
        self._calibration = calibration

    def set_input_profile(self, profile: InputProfile) -> None:
        """Replace the game InputProfile (e.g., after switching active game)."""
        self._input_profile = profile

    # ── IInputMapper ──────────────────────────────────────────────────────────

    def map(
        self,
        result_set: GestureResultSet,
        calibration: Optional[CalibrationProfile],
        profile: InputProfile,
    ) -> ControllerInput:
        """
        Convert gesture results to a complete controller snapshot.

        Steps
        -----
        1. For each axis binding in ``profile``:
           a. Retrieve GestureResult from ``result_set``.
           b. Apply calibration offset if available.
           c. Apply scale and inversion.
           d. Apply deadzone.
           e. Clamp to valid range.
        2. For each button binding in ``profile``:
           a. Retrieve GestureResult.is_active from ``result_set``.
        3. Assemble AxisValues + ButtonState → ControllerInput.
        """
        raise NotImplementedError

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _apply_deadzone(value: float, deadzone: float) -> float:
        """Return 0.0 if abs(value) < deadzone, else return value unchanged."""
        return 0.0 if abs(value) < deadzone else value

    @staticmethod
    def _clamp(value: float, low: float = -1.0, high: float = 1.0) -> float:
        """Clamp value to [low, high]."""
        return max(low, min(high, value))


class ControllerService:
    """
    EventBus bridge: GestureRecognizedEvent → InputMapper → IVirtualController.

    Parameters
    ----------
    input_mapper:
        Configured InputMapper instance.
    controller:
        An IVirtualController (XboxController or NullController).
    event_bus:
        The application-wide EventBus.
    """

    def __init__(
        self,
        input_mapper: InputMapper,
        controller: IVirtualController,
        event_bus: EventBus,
    ) -> None:
        self._mapper = input_mapper
        self._controller = controller
        self._bus = event_bus

    def register(self) -> None:
        """Subscribe to the EventBus. Call once during application startup."""
        from core.events import GestureRecognizedEvent
        self._bus.subscribe(GestureRecognizedEvent, self.on_gesture_recognized)
        logger.info("ControllerService registered on EventBus.")

    def on_gesture_recognized(self, event) -> None:
        """
        Map gesture results to controller input and send to the virtual device.
        """
        raise NotImplementedError
