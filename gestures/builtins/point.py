"""
gesturedrive.gestures.builtins.point
====================================
PointGesture: Built-in gesture recognizer for detecting a pointing index finger pose.
"""

from __future__ import annotations

import logging

from analysis.finger_state import FingerPosition, HandAnalysis
from gestures.base import Gesture
from gestures.gesture_result import GestureResult
from gestures.builtins.utils import calculate_quality_and_stability, extract_handedness

logger = logging.getLogger(__name__)


class PointGesture(Gesture):
    """
    Gesture recognizer for detecting a Point pose.

    Detection Rules
    ---------------
    - Index finger must be EXTENDED (tolerating slight bend as PARTIALLY_BENT).
    - Middle, Ring, and Pinky fingers must be CURLED (tolerating at most one PARTIALLY_BENT finger).
    - Middle, Ring, and Pinky fingers must NOT be EXTENDED.
    - Thumb position is flexible (EXTENDED, PARTIALLY_BENT, CURLED, or UNKNOWN).

    Confidence Calculation
    ----------------------
    - Evaluates extension quality of the Index finger.
    - Evaluates curl quality of the Middle, Ring, and Pinky fingers.
    - Factors in individual finger position confidences and landmark stability.
    """

    def __init__(self, priority: int = 40, enabled: bool = True) -> None:
        super().__init__(name="Point", priority=priority, enabled=enabled)

    def recognize(self, hand_analysis: HandAnalysis) -> GestureResult:
        """
        Analyze hand state and evaluate whether a Point gesture is performed.

        Parameters
        ----------
        hand_analysis: HandAnalysis
            Analyzed finger states and hand state metadata for a single hand.

        Returns
        -------
        GestureResult
            Result indicating detection status, confidence score, timestamp, and handedness.
        """
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
            )

        # 2. Middle, Ring, Pinky must NOT be EXTENDED or UNKNOWN
        other_fingers = [
            hand_analysis.middle,
            hand_analysis.ring,
            hand_analysis.pinky,
        ]
        for f in other_fingers:
            if f.position in (FingerPosition.EXTENDED, FingerPosition.UNKNOWN):
                return GestureResult(
                    gesture_name=self.name,
                    detected=False,
                    confidence=0.0,
                    timestamp=timestamp,
                    handedness=handedness,
                )

        curled_count = sum(1 for f in other_fingers if f.position == FingerPosition.CURLED)
        partially_bent_count = sum(1 for f in other_fingers if f.position == FingerPosition.PARTIALLY_BENT)

        # Must have at least 2 non-index fingers CURLED with at most 1 PARTIALLY_BENT
        if not (curled_count >= 2 and partially_bent_count <= 1):
            return GestureResult(
                gesture_name=self.name,
                detected=False,
                confidence=0.0,
                timestamp=timestamp,
                handedness=handedness,
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
        # Index extension factor
        index_pos = hand_analysis.index.position
        if index_pos == FingerPosition.EXTENDED:
            index_score = 1.0
        elif index_pos == FingerPosition.PARTIALLY_BENT:
            index_score = 0.70
        else:
            index_score = 0.0

        # Other fingers curl factor
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
                other_scores.append(0.60)
            else:
                other_scores.append(0.0)

        other_score = sum(other_scores) / len(other_scores)

        pose_score = 0.50 * index_score + 0.50 * other_score

        # Quality & Stability factor across all 5 fingers
        all_fingers = [
            hand_analysis.thumb,
            hand_analysis.index,
            hand_analysis.middle,
            hand_analysis.ring,
            hand_analysis.pinky,
        ]
        quality_stability = calculate_quality_and_stability(all_fingers)

        final_score = pose_score * quality_stability
        return round(max(0.0, min(1.0, final_score)), 2)
