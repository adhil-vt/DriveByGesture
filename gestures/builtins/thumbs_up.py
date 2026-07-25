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
from gestures.builtins.utils import calculate_quality_and_stability, extract_handedness

logger = logging.getLogger(__name__)


class ThumbsUpGesture(Gesture):
    """
    Gesture recognizer for detecting a Thumbs Up pose.

    Detection Rules
    ---------------
    - Thumb finger must be EXTENDED (tolerating slight bend as PARTIALLY_BENT).
    - Index, Middle, Ring, and Pinky fingers must be CURLED (tolerating at most one PARTIALLY_BENT finger).
    - Non-thumb fingers must NOT be EXTENDED or UNKNOWN.
    - Thumb must NOT be CURLED or UNKNOWN.

    Confidence Calculation
    ----------------------
    - Evaluates extension quality of the Thumb.
    - Evaluates curl quality of Index, Middle, Ring, and Pinky fingers.
    - Factors in individual finger position confidences and landmark stability.
    """

    def __init__(self, priority: int = 80, enabled: bool = True) -> None:
        super().__init__(name="Thumbs Up", priority=priority, enabled=enabled)

    def recognize(self, hand_analysis: HandAnalysis) -> GestureResult:
        """
        Analyze hand state and evaluate whether a Thumbs Up gesture is performed.

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

        # 1. Thumb must be EXTENDED or PARTIALLY_BENT (cannot be CURLED or UNKNOWN)
        thumb_pos = hand_analysis.thumb.position
        if thumb_pos in (FingerPosition.CURLED, FingerPosition.UNKNOWN):
            return GestureResult(
                gesture_name=self.name,
                detected=False,
                confidence=0.0,
                timestamp=timestamp,
                handedness=handedness,
            )

        # 2. Non-thumb fingers (Index, Middle, Ring, Pinky) must NOT be EXTENDED or UNKNOWN
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
                curl_scores.append(0.60)
            else:
                curl_scores.append(0.0)

        curl_factor = sum(curl_scores) / len(curl_scores)

        pose_score = 0.40 * thumb_score + 0.60 * curl_factor

        # Quality & Stability factor across all 5 fingers
        all_fingers = [hand_analysis.thumb] + non_thumb_fingers
        quality_stability = calculate_quality_and_stability(all_fingers)

        final_score = pose_score * quality_stability
        return round(max(0.0, min(1.0, final_score)), 2)
