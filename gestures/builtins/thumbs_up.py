"""
gesturedrive.gestures.builtins.thumbs_up
========================================
ThumbsUpGesture: Built-in gesture recognizer for detecting a thumbs-up pose.
"""

from __future__ import annotations

import logging

from analysis.finger_state import FingerPosition, HandAnalysis
from gestures.base import Gesture
from gestures.gesture_result import GestureResult
from gestures.builtins.utils import (
    calculate_quality_and_stability,
    distance_3d,
    extract_handedness,
    get_hand_scale,
    get_thumb_vertical_direction,
)

logger = logging.getLogger(__name__)


class ThumbsUpGesture(Gesture):
    """
    Gesture recognizer for detecting a Thumbs Up pose.

    Detection Rules
    ---------------
    - Thumb finger must be EXTENDED (tolerating slight bend as PARTIALLY_BENT).
    - Thumb must point UPWARDS in camera space and project above Index MCP.
    - Thumb must be clearly extended from MCP to Tip (cannot be folded across palm).
    - Index, Middle, Ring, and Pinky fingers must be CURLED (tolerating at most one PARTIALLY_BENT finger).
    - Non-thumb fingers must NOT be EXTENDED or UNKNOWN.
    - Thumb must NOT be CURLED or UNKNOWN.
    """

    def __init__(self, priority: int = 80, enabled: bool = True) -> None:
        super().__init__(name="Thumbs Up", priority=priority, enabled=enabled)

    def recognize(self, hand_analysis: HandAnalysis) -> GestureResult:
        timestamp = getattr(hand_analysis, "timestamp", 0.0)
        handedness = extract_handedness(hand_analysis)

        # 1. Thumb must be EXTENDED or PARTIALLY_BENT (cannot be CURLED or UNKNOWN)
        thumb_pos = hand_analysis.thumb.position
        if thumb_pos in (FingerPosition.CURLED, FingerPosition.UNKNOWN):
            return GestureResult(
                gesture_name=self.name,
                detected=False,
                confidence=0.0,
                timestamp=timestamp,
                handedness=handedness,
                rejection_reason="Thumb not extended",
            )

        # 2. Check vertical orientation & palm elevation: Thumb must point UP and project above palm
        if hasattr(hand_analysis, "hand_state") and hand_analysis.hand_state:
            v_dir = get_thumb_vertical_direction(hand_analysis.hand_state)
            if v_dir != "UP":
                return GestureResult(
                    gesture_name=self.name,
                    detected=False,
                    confidence=0.0,
                    timestamp=timestamp,
                    handedness=handedness,
                    rejection_reason="Thumb not pointing up",
                )

            # Ensure Thumb Tip is elevated above Index MCP and physically extended
            lms = getattr(hand_analysis.hand_state, "landmarks", None)
            if lms and len(lms) >= 21:
                scale = get_hand_scale(hand_analysis.hand_state)
                thumb_mcp = lms[2]
                thumb_tip = lms[4]
                index_mcp = lms[5]

                norm_elevation = (index_mcp.y - thumb_tip.y) / max(0.001, scale)
                if norm_elevation < 0.20:
                    return GestureResult(
                        gesture_name=self.name,
                        detected=False,
                        confidence=0.0,
                        timestamp=timestamp,
                        handedness=handedness,
                        rejection_reason="Thumb not elevated above palm",
                    )

                thumb_span = distance_3d(thumb_mcp, thumb_tip) / max(0.001, scale)
                if thumb_span < 0.30:
                    return GestureResult(
                        gesture_name=self.name,
                        detected=False,
                        confidence=0.0,
                        timestamp=timestamp,
                        handedness=handedness,
                        rejection_reason="Thumb not extended",
                    )

        # 3. Non-thumb fingers (Index, Middle, Ring, Pinky) must NOT be EXTENDED or UNKNOWN
        non_thumb_fingers = [
            hand_analysis.index,
            hand_analysis.middle,
            hand_analysis.ring,
            hand_analysis.pinky,
        ]
        for f in non_thumb_fingers:
            if f.position in (FingerPosition.EXTENDED, FingerPosition.UNKNOWN):
                return GestureResult(
                    gesture_name=self.name,
                    detected=False,
                    confidence=0.0,
                    timestamp=timestamp,
                    handedness=handedness,
                    rejection_reason=f"{f.name.name.title()} finger extended",
                )

        curled_count = sum(1 for f in non_thumb_fingers if f.position == FingerPosition.CURLED)
        partially_bent_count = sum(1 for f in non_thumb_fingers if f.position == FingerPosition.PARTIALLY_BENT)

        # Require at least 3 non-thumb fingers to be CURLED with at most 1 PARTIALLY_BENT
        if not (curled_count >= 3 and partially_bent_count <= 1):
            return GestureResult(
                gesture_name=self.name,
                detected=False,
                confidence=0.0,
                timestamp=timestamp,
                handedness=handedness,
                rejection_reason="Fingers not fully folded",
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
        """
        Calculate a normalized confidence score in range [0.0, 1.0].
        """
        # Thumb extension factor
        thumb_pos = hand_analysis.thumb.position
        if thumb_pos == FingerPosition.EXTENDED:
            thumb_score = 1.0
        elif thumb_pos == FingerPosition.PARTIALLY_BENT:
            thumb_score = 0.75
        else:
            thumb_score = 0.0

        # Non-thumb curl factor
        non_thumb_fingers = [
            hand_analysis.index,
            hand_analysis.middle,
            hand_analysis.ring,
            hand_analysis.pinky,
        ]
        curl_scores = []
        for f in non_thumb_fingers:
            if f.position == FingerPosition.CURLED:
                curl_scores.append(1.0)
            elif f.position == FingerPosition.PARTIALLY_BENT:
                curl_scores.append(0.80)
            else:
                curl_scores.append(0.0)

        curl_factor = sum(curl_scores) / len(curl_scores)

        pose_score = 0.50 * thumb_score + 0.50 * curl_factor

        # Quality & Stability factor focused on primary active fingers
        active_fingers = [hand_analysis.thumb, hand_analysis.index, hand_analysis.middle]
        quality_stability = calculate_quality_and_stability(active_fingers)

        final_score = pose_score * quality_stability
        return round(max(0.0, min(1.0, final_score)), 2)
