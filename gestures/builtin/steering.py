"""
gesturedrive.gesture.builtin.steering
========================================
SteeringRecognizer: computes steering angle from palm roll orientation.

Algorithm sketch (implementation phase)
-----------------------------------------
1. Extract wrist (landmark 0) and middle-finger MCP (landmark 9) positions.
2. Compute the vector from wrist → MCP in the XY plane.
3. Calculate the signed angle of this vector relative to the vertical axis.
4. Apply calibration offsets (neutral_palm_normal) to zero the center.
5. Normalise to [-1.0, 1.0] using calibrated max left/right angles.
6. Apply an optional smoothing filter (configurable alpha).

Gesture contract
----------------
gesture_name : "steering"
value        : float in [-1.0, 1.0]  (left = negative, right = positive)
active       : always True when a hand is detected
"""

from __future__ import annotations

from typing import Optional

from core.interfaces import IGestureRecognizer
from core.models import CalibrationProfile, GestureResult, HandState


class SteeringRecognizer(IGestureRecognizer):
    """
    Computes the steering angle from wrist roll in the camera plane.

    Parameters
    ----------
    smoothing_alpha:
        Exponential moving average factor [0.0, 1.0].
        0.0 = no smoothing (raw), 1.0 = fully frozen.
        Default 0.15 (configurable via GestureConfig).
    preferred_hand:
        ``"left"``, ``"right"``, or ``"any"`` — which hand drives steering.
    """

    def __init__(
        self,
        smoothing_alpha: float = 0.15,
        preferred_hand: str = "right",
    ) -> None:
        self._smoothing_alpha = smoothing_alpha
        self._preferred_hand = preferred_hand
        self._last_value: float = 0.0

    @property
    def gesture_name(self) -> str:
        return "steering"

    @property
    def display_name(self) -> str:
        return "Steering"

    def recognize(
        self,
        hand_state: HandState,
        calibration: Optional[CalibrationProfile] = None,
    ) -> Optional[GestureResult]:
        """
        Compute steering angle from palm roll.

        Returns None if no suitable hand is present in hand_state.
        """
        raise NotImplementedError
