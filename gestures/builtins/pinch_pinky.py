"""
gesturedrive.gestures.builtins.pinch_pinky
==========================================
PinchPinkyGesture: Built-in gesture recognizer for detecting natural pinch pose between thumb tip and pinky tip (Pinch Pinky for Right Click).
"""

from __future__ import annotations

import logging
import math
from typing import Optional

from analysis.finger_state import FingerPosition, HandAnalysis
from config.schema import GestureConfig
from gestures.base import Gesture
from gestures.builtins.utils import (
    calculate_quality_and_stability,
    distance_3d,
    extract_handedness,
    get_hand_scale,
)
from gestures.gesture_result import GestureResult

logger = logging.getLogger(__name__)


class PinchPinkyGesture(Gesture):
    """
    Gesture recognizer for detecting a natural Pinch Pinky pose (Thumb Tip ↔ Pinky Tip).

    Detection Rules
    ---------------
    - Thumb Tip (4) and Pinky Tip (20) 3D distance must be <= 0.38 * scale.
    - Thumb Tip (4) and Index Tip (8) distance must be >= 0.45 * scale (guarantees zero conflict with Left Click/Drag).
    - Pinky finger position must be EXTENDED, PARTIALLY_BENT, or CURLED (cannot be UNKNOWN).
    """

    def __init__(
        self,
        priority: int = 85,
        enabled: bool = True,
        config: Optional[GestureConfig] = None,
    ) -> None:
        super().__init__(name="Pinch Pinky", priority=priority, enabled=enabled)
        self._config = config or GestureConfig()

    def recognize(self, hand_analysis: HandAnalysis) -> GestureResult:
        timestamp = getattr(hand_analysis, "timestamp", 0.0)
        handedness = extract_handedness(hand_analysis)

        if not hasattr(hand_analysis, "hand_state") or not hand_analysis.hand_state:
            return GestureResult(
                gesture_name=self.name,
                detected=False,
                confidence=0.0,
                timestamp=timestamp,
                handedness=handedness,
                rejection_reason="No hand landmark state",
            )

        lms = hand_analysis.hand_state.landmarks
        if len(lms) < 21:
            return GestureResult(
                gesture_name=self.name,
                detected=False,
                confidence=0.0,
                timestamp=timestamp,
                handedness=handedness,
                rejection_reason="Insufficient landmarks",
            )

        scale = get_hand_scale(hand_analysis.hand_state)
        if scale <= 0:
            scale = 1.0

        d_thumb_pinky = distance_3d(lms[4], lms[20]) / scale
        d_thumb_index = distance_3d(lms[4], lms[8]) / scale

        # 1. Zero Conflict Guard: Index Tip must NOT be pinched to Thumb Tip
        if d_thumb_index < 0.45:
            return GestureResult(
                gesture_name=self.name,
                detected=False,
                confidence=0.0,
                timestamp=timestamp,
                handedness=handedness,
                rejection_reason="Index tip too close to thumb (Index Pinch active)",
            )

        # 2. Pinky Pinch Distance Rule: Thumb Tip ↔ Pinky Tip <= 0.38 * scale
        max_dist = 0.38
        if d_thumb_pinky > max_dist:
            return GestureResult(
                gesture_name=self.name,
                detected=False,
                confidence=0.0,
                timestamp=timestamp,
                handedness=handedness,
                rejection_reason="Thumb and Pinky tips too far apart",
            )

        # Compute continuous Cosine Decay confidence score
        norm_ratio = d_thumb_pinky / max_dist
        pose_score = 0.5 * (1.0 + math.cos(math.pi * norm_ratio))

        # Focus quality & stability on active fingers (Thumb, Pinky, Index)
        active_fingers = [hand_analysis.thumb, hand_analysis.pinky, hand_analysis.index]
        quality_stability = calculate_quality_and_stability(active_fingers)

        final_score = pose_score * quality_stability
        confidence = round(max(0.0, min(1.0, final_score)), 2)

        return GestureResult(
            gesture_name=self.name,
            detected=True,
            confidence=confidence,
            timestamp=timestamp,
            handedness=handedness,
        )
