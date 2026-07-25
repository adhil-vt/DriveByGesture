"""
gesturedrive.gesture.builtin.brake
=====================================
BrakeRecognizer: detects an open flat palm pushed toward the camera.

Algorithm sketch (implementation phase)
-----------------------------------------
1. Check that all 5 fingertips are above their respective MCP joints
   (fingers fully extended — open palm).
2. Compute the Z-depth of the palm centroid (average of landmarks 0, 5, 9, 13, 17).
3. If Z < brake_z_threshold (palm is close to / pushed toward camera), activate.
4. Map proximity to a [0.0, 1.0] brake value using calibrated z range.

Gesture contract
----------------
gesture_name : "brake"
value        : float in [0.0, 1.0]  (0 = released, 1 = full brake)
active       : True when value > 0.1
"""

from __future__ import annotations

from typing import Optional

from core.interfaces import IGestureRecognizer
from core.models import CalibrationProfile, GestureResult, HandState


class BrakeRecognizer(IGestureRecognizer):
    """
    Detects an open palm push toward the camera as a braking gesture.

    Parameters
    ----------
    z_threshold:
        Normalized Z-depth below which the gesture is considered active.
        Overridden by CalibrationProfile.brake_z_threshold if available.
    """

    def __init__(self, z_threshold: float = -0.10) -> None:
        self._z_threshold = z_threshold

    @property
    def gesture_name(self) -> str:
        return "brake"

    @property
    def display_name(self) -> str:
        return "Brake"

    def recognize(
        self,
        hand_state: HandState,
        calibration: Optional[CalibrationProfile] = None,
    ) -> Optional[GestureResult]:
        """Detect open-palm push. Returns None if hand not present."""
        raise NotImplementedError
