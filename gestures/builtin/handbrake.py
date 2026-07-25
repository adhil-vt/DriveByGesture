"""
gesturedrive.gesture.builtin.handbrake
=========================================
HandbrakeRecognizer: detects a specific multi-finger pose for handbrake.

Algorithm sketch (implementation phase)
-----------------------------------------
Proposed pose: index finger fully extended, remaining fingers curled,
thumb pointing sideways (gun-finger shape with thumb up).

1. Verify index fingertip is above index MCP (extended).
2. Verify middle, ring, pinky fingertips are below their MCPs (curled).
3. Verify thumb tip is laterally displaced (thumb extended outward).
4. All conditions must hold for ``hold_frames`` consecutive frames.

Gesture contract
----------------
gesture_name : "handbrake"
value        : None  (boolean gesture)
active       : True while the pose is held
"""

from __future__ import annotations

from typing import Optional

from core.interfaces import IGestureRecognizer
from core.models import CalibrationProfile, GestureResult, HandState


class HandbrakeRecognizer(IGestureRecognizer):
    """
    Detects a held gun-finger pose as the handbrake button.

    Parameters
    ----------
    hold_frames:
        Number of consecutive frames the pose must be held before
        the gesture is reported as active (debouncing).
    """

    def __init__(self, hold_frames: int = 3) -> None:
        self._hold_frames = hold_frames
        self._frame_count: int = 0

    @property
    def gesture_name(self) -> str:
        return "handbrake"

    @property
    def display_name(self) -> str:
        return "Handbrake"

    def recognize(
        self,
        hand_state: HandState,
        calibration: Optional[CalibrationProfile] = None,
    ) -> Optional[GestureResult]:
        """Detect gun-finger pose with debouncing."""
        raise NotImplementedError
