"""
gesturedrive.calibration.calibrator
======================================
CalibrationOrchestrator: drives the multi-step calibration workflow.

Steps (in order)
-----------------
0. Neutral Position        — palm flat, facing camera
1. Maximum Steering Left   — tilt hand fully left
2. Maximum Steering Right  — tilt hand fully right
3. Full Throttle           — curl all fingers into a fist
4. Open Palm (Brake)       — splay fingers toward camera

Flow
----
1. ``start()``  — reset state, begin at step 0, subscribe to HandDetectedEvent.
2. For each frame: forward HandState to the current CalibrationSession.
3. When session.is_complete: auto-advance or wait for UI confirmation.
4. ``advance()`` — called by UI when user clicks "Next".
5. When all steps complete: validate with CalibrationValidator.
6. On valid: publish CalibrationCompleteEvent, unsubscribe from HandDetectedEvent.
7. On invalid: publish ErrorEvent with user_message, reset to step 0.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from calibration.profile import CalibrationProfile
from calibration.session import CalibrationSession
from calibration.validators import CalibrationValidator
from core.event_bus import EventBus
from core.events import (
    CalibrationCompleteEvent,
    CalibrationStepChangedEvent,
    ErrorEvent,
    HandDetectedEvent,
)
from core.exceptions import CalibrationError
from core.interfaces import ICalibrator

logger = logging.getLogger(__name__)

_SOURCE_ID = "calibration.calibrator"

# Ordered list of (pose_name, display_name) pairs
CALIBRATION_STEPS = [
    ("neutral_position",      "Neutral Position"),
    ("max_steering_left",     "Maximum Steering Left"),
    ("max_steering_right",    "Maximum Steering Right"),
    ("full_throttle",         "Full Throttle (Fist)"),
    ("open_palm_brake",       "Open Palm (Brake)"),
]


class CalibrationOrchestrator(ICalibrator):
    """
    Manages the full calibration sequence.

    Parameters
    ----------
    event_bus:
        The application-wide EventBus.
    validator:
        CalibrationValidator used after all steps complete.
    frames_per_step:
        How many good frames to collect per pose. Default: 90.
    """

    def __init__(
        self,
        event_bus: EventBus,
        validator: Optional[CalibrationValidator] = None,
        frames_per_step: int = 90,
    ) -> None:
        self._bus = event_bus
        self._validator = validator or CalibrationValidator()
        self._frames_per_step = frames_per_step

        self._sessions: List[CalibrationSession] = []
        self._current_step: int = 0
        self._profile_data: dict = {}
        self._active: bool = False

    # ── ICalibrator ───────────────────────────────────────────────────────────

    def start(self) -> None:
        """Begin calibration from step 0."""
        raise NotImplementedError

    def advance(self) -> None:
        """Confirm the current step and move to the next."""
        raise NotImplementedError

    def cancel(self) -> None:
        """Abort calibration without saving."""
        raise NotImplementedError

    @property
    def current_step(self) -> int:
        return self._current_step

    @property
    def is_complete(self) -> bool:
        return self._current_step >= len(CALIBRATION_STEPS)

    # ── EventBus handler ─────────────────────────────────────────────────────

    def _on_hand_detected(self, event: HandDetectedEvent) -> None:
        """Forward each frame to the current CalibrationSession."""
        raise NotImplementedError

    # ── Private helpers ───────────────────────────────────────────────────────

    def _build_profile(self) -> CalibrationProfile:
        """Assemble a CalibrationProfile from all collected session baselines."""
        raise NotImplementedError
