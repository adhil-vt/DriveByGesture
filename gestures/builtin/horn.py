"""
gesturedrive.gesture.builtin.horn
====================================
HornRecognizer: detects a thumbs-up gesture to trigger the horn.

Algorithm sketch (implementation phase)
-----------------------------------------
1. Verify thumb tip is significantly above the thumb IP joint (extended up).
2. Verify all 4 fingers are curled (fingertips below MCPs).
3. Optionally verify the thumb is pointing vertically (not laterally —
   to distinguish from handbrake gun-finger).

Gesture contract
----------------
gesture_name : "horn"
value        : None  (boolean gesture)
active       : True while the thumbs-up pose is held
"""

from __future__ import annotations

from typing import Optional

from core.interfaces import IGestureRecognizer
from core.models import CalibrationProfile, GestureResult, HandState


class HornRecognizer(IGestureRecognizer):
    """
    Detects a thumbs-up pose as the horn button.

    Parameters
    ----------
    hold_frames:
        Consecutive frames required to activate (debouncing).
    """

    def __init__(self, hold_frames: int = 2) -> None:
        self._hold_frames = hold_frames
        self._frame_count: int = 0

    @property
    def gesture_name(self) -> str:
        return "horn"

    @property
    def display_name(self) -> str:
        return "Horn"

    def recognize(
        self,
        hand_state: HandState,
        calibration: Optional[CalibrationProfile] = None,
    ) -> Optional[GestureResult]:
        """Detect thumbs-up pose."""
        raise NotImplementedError
