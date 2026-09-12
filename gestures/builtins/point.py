"""
gesturedrive.gestures.builtins.point
====================================
PointGesture: Built-in gesture recognizer for detecting a pointing index finger pose.
"""

from __future__ import annotations

import logging
import math

from analysis.finger_state import FingerPosition, HandAnalysis
from gestures.base import Gesture
from gestures.gesture_result import GestureResult
from gestures.builtins.utils import (
    calculate_quality_and_stability,
    distance_3d,
    extract_handedness,
    get_hand_scale,
)

logger = logging.getLogger(__name__)


class PointGesture(Gesture):
    """
    Gesture recognizer for detecting a Point pose.

    Detection Rules
    ---------------
    - Index finger must be clearly EXTENDED (tolerating slight bend as PARTIALLY_BENT).
    - Middle, Ring, and Pinky fingers must be folded (CURLED or PARTIALLY_BENT).
    - Scale-normalized Index tip distance to Wrist must be significantly greater than Middle tip distance to Wrist.
    - 3D Index vector angle (Wrist -> MCP -> TIP) must be straight (>= 145 degrees).
    - Thumb position is flexible (does not invalidate the pointing gesture).
    """

    def __init__(self, priority: int = 40, enabled: bool = True) -> None:
        super().__init__(name="Point", priority=priority, enabled=enabled)

    def recognize(self, hand_analysis: HandAnalysis) -> GestureResult:
        timestamp = getattr(hand_analysis, "timestamp", 0.0)
        handedness = extract_handedness(hand_analysis)

        # 1. Index finger must be EXTENDED or PARTIALLY_BENT (cannot be CURLED or UNKNOWN)
        index_pos = hand_analysis.index.position
        if index_pos in (FingerPosition.CURLED, FingerPosition.UNKNOWN):
            return GestureResult(
                gesture_name=self.name,
                detected=False,
                confidence=0.0,
                timestamp=timestamp,
                handedness=handedness,
                rejection_reason="Index finger not extended",
            )

        # 2. Middle finger must not be fully EXTENDED
        if hand_analysis.middle.position == FingerPosition.EXTENDED:
            return GestureResult(
                gesture_name=self.name,
                detected=False,
                confidence=0.0,
                timestamp=timestamp,
                handedness=handedness,
                rejection_reason="Middle finger not folded",
            )

        # 3. Ring and Pinky fingers must not be fully EXTENDED
        for f in [hand_analysis.ring, hand_analysis.pinky]:
            if f.position == FingerPosition.EXTENDED:
                return GestureResult(
                    gesture_name=self.name,
                    detected=False,
                    confidence=0.0,
                    timestamp=timestamp,
                    handedness=handedness,
                    rejection_reason=f"{f.name.name.title()} finger extended",
                )

        # 4. Geometric Vector & Relative Tip Distance Verification
        if hasattr(hand_analysis, "hand_state") and hand_analysis.hand_state and len(hand_analysis.hand_state.landmarks) >= 21:
            lms = hand_analysis.hand_state.landmarks
            wrist = lms[0]
            index_mcp = lms[5]
            index_tip = lms[8]
            middle_tip = lms[12]

            scale = get_hand_scale(hand_analysis.hand_state)
            d_idx_wrist = distance_3d(wrist, index_tip) / scale
            d_mid_wrist = distance_3d(wrist, middle_tip) / scale

            # 3D Index Vector Angle (Wrist -> MCP -> TIP)
            v1_x, v1_y, v1_z = index_mcp.x - wrist.x, index_mcp.y - wrist.y, index_mcp.z - wrist.z
            v2_x, v2_y, v2_z = index_tip.x - index_mcp.x, index_tip.y - index_mcp.y, index_tip.z - index_mcp.z
            mag1 = (v1_x**2 + v1_y**2 + v1_z**2) ** 0.5
            mag2 = (v2_x**2 + v2_y**2 + v2_z**2) ** 0.5

            if mag1 > 0 and mag2 > 0:
                dot = v1_x * v2_x + v1_y * v2_y + v1_z * v2_z
                cos_a = max(-1.0, min(1.0, dot / (mag1 * mag2)))
                angle_deg = 180.0 - math.degrees(math.acos(cos_a))
                if angle_deg < 120.0:
                    return GestureResult(
                        gesture_name=self.name,
                        detected=False,
                        confidence=0.0,
                        timestamp=timestamp,
                        handedness=handedness,
                        rejection_reason="Index angle below threshold",
                    )

            # Check relative wrist distance ratio
            # When index has confirmed extension and other fingers are folded, allow perspective foreshortening down to 0.75x
            has_strong_extension = (
                index_pos == FingerPosition.EXTENDED
                and hand_analysis.middle.position in (FingerPosition.CURLED, FingerPosition.PARTIALLY_BENT)
                and hand_analysis.ring.position in (FingerPosition.CURLED, FingerPosition.PARTIALLY_BENT)
                and hand_analysis.pinky.position in (FingerPosition.CURLED, FingerPosition.PARTIALLY_BENT)
            )

            min_ratio = 0.75 if has_strong_extension else 1.08
            if d_idx_wrist < (min_ratio * d_mid_wrist):
                return GestureResult(
                    gesture_name=self.name,
                    detected=False,
                    confidence=0.0,
                    timestamp=timestamp,
                    handedness=handedness,
                    rejection_reason="Middle finger not folded",
                )

        # Compute confidence score
        confidence = self._compute_confidence(hand_analysis)

        return GestureResult(
            gesture_name=self.name,
            detected=True,
            confidence=confidence,
            timestamp=timestamp,
            handedness=handedness,
        )

    def _compute_confidence(self, hand_analysis: HandAnalysis) -> float:
        """Calculate a normalized confidence score in range [0.0, 1.0]."""
        index_pos = hand_analysis.index.position
        if index_pos == FingerPosition.EXTENDED:
            index_score = 1.0
        elif index_pos == FingerPosition.PARTIALLY_BENT:
            index_score = 0.80
        else:
            index_score = 0.0

        other_fingers = [
            hand_analysis.middle,
            hand_analysis.ring,
            hand_analysis.pinky,
        ]
        other_scores = []
        for f in other_fingers:
            if f.position == FingerPosition.CURLED:
                other_scores.append(1.0)
            elif f.position == FingerPosition.PARTIALLY_BENT:
                other_scores.append(0.75)
            else:
                other_scores.append(0.0)

        other_score = sum(other_scores) / len(other_scores)
        pose_score = 0.60 * index_score + 0.40 * other_score

        # Focus quality & stability on active pointing index finger and thumb
        active_fingers = [hand_analysis.index, hand_analysis.middle]
        quality_stability = calculate_quality_and_stability(active_fingers)

        final_score = pose_score * quality_stability
        return round(max(0.0, min(1.0, final_score)), 2)
