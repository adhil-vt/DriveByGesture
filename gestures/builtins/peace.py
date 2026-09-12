"""
gesturedrive.gestures.builtins.peace
====================================
PeaceGesture: Built-in gesture recognizer for detecting a Victory / Peace sign pose.
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
)

logger = logging.getLogger(__name__)


class PeaceGesture(Gesture):
    """
    Gesture recognizer for detecting a Peace (V-sign) pose.

    Detection Rules
    ---------------
    - Index and Middle fingers must be EXTENDED (tolerating at most one PARTIALLY_BENT finger).
    - Ring and Pinky fingers must be CURLED (tolerating at most one PARTIALLY_BENT finger).
    - Ring and Pinky fingers must NOT be EXTENDED.
    - Index and Middle fingers must NOT be CURLED or UNKNOWN.
    - Index Tip (8) and Middle Tip (12) must be separated (V-shape).
    """

    def __init__(self, priority: int = 50, enabled: bool = True) -> None:
        super().__init__(name="Peace", priority=priority, enabled=enabled)

    def recognize(self, hand_analysis: HandAnalysis) -> GestureResult:
        timestamp = getattr(hand_analysis, "timestamp", 0.0)
        handedness = extract_handedness(hand_analysis)

        # 1. Index and Middle fingers must be EXTENDED or PARTIALLY_BENT (cannot be CURLED or UNKNOWN)
        extended_pair = [hand_analysis.index, hand_analysis.middle]
        for f in extended_pair:
            if f.position in (FingerPosition.CURLED, FingerPosition.UNKNOWN):
                return GestureResult(
                    gesture_name=self.name,
                    detected=False,
                    confidence=0.0,
                    timestamp=timestamp,
                    handedness=handedness,
                    rejection_reason="Index/Middle not extended",
                )

        ext_count = sum(1 for f in extended_pair if f.position == FingerPosition.EXTENDED)
        ext_partially_bent = sum(1 for f in extended_pair if f.position == FingerPosition.PARTIALLY_BENT)
        if not (ext_count >= 1 and ext_partially_bent <= 1):
            return GestureResult(
                gesture_name=self.name,
                detected=False,
                confidence=0.0,
                timestamp=timestamp,
                handedness=handedness,
                rejection_reason="Index/Middle not extended",
            )

        # 2. Ring and Pinky fingers must NOT be EXTENDED or UNKNOWN
        curled_pair = [hand_analysis.ring, hand_analysis.pinky]
        for f in curled_pair:
            if f.position in (FingerPosition.EXTENDED, FingerPosition.UNKNOWN):
                return GestureResult(
                    gesture_name=self.name,
                    detected=False,
                    confidence=0.0,
                    timestamp=timestamp,
                    handedness=handedness,
                    rejection_reason=f"{f.name.name.title()} finger extended",
                )

        curl_count = sum(1 for f in curled_pair if f.position == FingerPosition.CURLED)
        curl_partially_bent = sum(1 for f in curled_pair if f.position == FingerPosition.PARTIALLY_BENT)
        if not (curl_count >= 1 and curl_partially_bent <= 1):
            return GestureResult(
                gesture_name=self.name,
                detected=False,
                confidence=0.0,
                timestamp=timestamp,
                handedness=handedness,
                rejection_reason="Ring/Pinky not folded",
            )

        # 3. Check V-shape separation between Index tip (8) and Middle tip (12)
        if hasattr(hand_analysis, "hand_state") and hand_analysis.hand_state and len(hand_analysis.hand_state.landmarks) >= 21:
            lms = hand_analysis.hand_state.landmarks
            scale = get_hand_scale(hand_analysis.hand_state)
            separation = distance_3d(lms[8], lms[12]) / scale
            if separation < 0.18:
                return GestureResult(
                    gesture_name=self.name,
                    detected=False,
                    confidence=0.0,
                    timestamp=timestamp,
                    handedness=handedness,
                    rejection_reason="Finger separation too small",
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
        # Index and Middle extension factor
        ext_pair = [hand_analysis.index, hand_analysis.middle]
        ext_scores = []
        for f in ext_pair:
            if f.position == FingerPosition.EXTENDED:
                ext_scores.append(1.0)
            elif f.position == FingerPosition.PARTIALLY_BENT:
                ext_scores.append(0.70)
            else:
                ext_scores.append(0.0)

        ext_factor = sum(ext_scores) / len(ext_scores)

        # Ring and Pinky curl factor
        curl_pair = [hand_analysis.ring, hand_analysis.pinky]
        curl_scores = []
        for f in curl_pair:
            if f.position == FingerPosition.CURLED:
                curl_scores.append(1.0)
            elif f.position == FingerPosition.PARTIALLY_BENT:
                curl_scores.append(0.60)
            else:
                curl_scores.append(0.0)

        curl_factor = sum(curl_scores) / len(curl_scores)

        pose_score = 0.55 * ext_factor + 0.45 * curl_factor

        # Quality & Stability factor focused on primary active V-sign fingers (Index, Middle, Ring, Pinky)
        active_fingers = [
            hand_analysis.index,
            hand_analysis.middle,
            hand_analysis.ring,
            hand_analysis.pinky,
        ]
        quality_stability = calculate_quality_and_stability(active_fingers)

        final_score = pose_score * quality_stability
        return round(max(0.0, min(1.0, final_score)), 2)
