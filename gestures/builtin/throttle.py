"""
gesturedrive.gesture.builtin.throttle
========================================
ThrottleRecognizer: maps finger curl ratio to throttle value [0.0, 1.0].

Algorithm sketch (implementation phase)
-----------------------------------------
1. For each of the 4 non-thumb fingers, compute the curl ratio:
   (distance from fingertip to palm base) / (finger fully extended length).
2. Average the 4 ratios to get an overall curl percentage.
3. Invert: 0 = fully curled (fist = max throttle), 1 = fully open (no throttle).
4. Apply calibration thresholds (throttle_open_ratio, throttle_closed_ratio).
5. Clamp to [0.0, 1.0].

Gesture contract
----------------
gesture_name : "throttle"
value        : float in [0.0, 1.0]  (0 = no throttle, 1 = full throttle)
active       : True when value > throttle_deadzone
"""

from __future__ import annotations

from typing import Optional

from core.interfaces import IGestureRecognizer
from core.models import CalibrationProfile, GestureResult, HandState


class ThrottleRecognizer(IGestureRecognizer):
    """
    Recognizes fist-closure as throttle input.

    Parameters
    ----------
    deadzone:
        Values below this threshold are reported as 0.0 (no throttle).
    preferred_hand:
        Which hand to read throttle from.
    """

    def __init__(
        self,
        deadzone: float = 0.05,
        preferred_hand: str = "right",
    ) -> None:
        self._deadzone = deadzone
        self._preferred_hand = preferred_hand

    @property
    def gesture_name(self) -> str:
        return "throttle"

    @property
    def display_name(self) -> str:
        return "Throttle"

    def recognize(
        self,
        hand_state: HandState,
        calibration: Optional[CalibrationProfile] = None,
    ) -> Optional[GestureResult]:
        """Compute throttle from finger curl. Returns None if no hand detected."""
        raise NotImplementedError
