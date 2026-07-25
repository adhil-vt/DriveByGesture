"""
gesturedrive.gestures.builtins.fist
===================================
FistGesture: Built-in gesture recognizer for detecting a closed fist pose.
"""

from __future__ import annotations

import logging

from analysis.finger_state import FingerPosition, HandAnalysis
from gestures.base import Gesture
from gestures.gesture_result import GestureResult
from gestures.builtins.utils import calculate_quality_and_stability, extract_handedness

logger = logging.getLogger(__name__)


class FistGesture(Gesture):
    """
    Gesture recognizer for detecting a Fist pose.

    Detection Rules
    ---------------
    - Index, Middle, Ring, and Pinky fingers must be CURLED (tolerating at most one PARTIALLY_BENT finger due to noise).
    - Thumb preferred CURLED, but tolerates CURLED, PARTIALLY_BENT, or UNKNOWN (due to occlusion).
    - No finger may be EXTENDED.

    Confidence Calculation
    ----------------------
    - Evaluates curl completeness across all 4 non-thumb fingers and the thumb.
    - Factors in individual finger position confidence scores.
    - Penalizes confidence if fingers are partially bent, if thumb is occluded/UNKNOWN,
      or if overall landmark stability is low.
    """

    def __init__(self, priority: int = 60, enabled: bool = True) -> None:
        super().__init__(name="Fist", priority=priority, enabled=enabled)

    def recognize(self, hand_analysis: HandAnalysis) -> GestureResult:
        """
        Analyze hand state and evaluate whether a Fist gesture is performed.

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

        fingers = [
            hand_analysis.thumb,
            hand_analysis.index,
            hand_analysis.middle,
            hand_analysis.ring,
            hand_analysis.pinky,
        ]

        # 1. No finger (thumb or non-thumb) can be EXTENDED in a fist
        for f in fingers:
            if f.position == FingerPosition.EXTENDED:
                return GestureResult(
                    gesture_name=self.name,
                    detected=False,
                    confidence=0.0,
                    timestamp=timestamp,
                    handedness=handedness,
                )

        # 2. Check Thumb tolerance: CURLED, PARTIALLY_BENT, or UNKNOWN
        thumb_valid = hand_analysis.thumb.position in (
            FingerPosition.CURLED,
            FingerPosition.PARTIALLY_BENT,
            FingerPosition.UNKNOWN,
        )
        if not thumb_valid:
            return GestureResult(
                gesture_name=self.name,
                detected=False,
                confidence=0.0,
                timestamp=timestamp,
                handedness=handedness,
            )

        # 3. Non-thumb fingers (Index, Middle, Ring, Pinky)
        non_thumb_fingers = [
            hand_analysis.index,
            hand_analysis.middle,
            hand_analysis.ring,
            hand_analysis.pinky,
        ]

        # Non-thumb fingers must not be UNKNOWN
        for f in non_thumb_fingers:
            if f.position == FingerPosition.UNKNOWN:
                return GestureResult(
                    gesture_name=self.name,
                    detected=False,
                    confidence=0.0,
                    timestamp=timestamp,
                    handedness=handedness,
                )

        curled_count = sum(1 for f in non_thumb_fingers if f.position == FingerPosition.CURLED)
        partially_bent_count = sum(1 for f in non_thumb_fingers if f.position == FingerPosition.PARTIALLY_BENT)

        # Require at least 3 non-thumb fingers to be CURLED, with at most 1 PARTIALLY_BENT
        if not (curled_count >= 3 and partially_bent_count <= 1):
            return GestureResult(
                gesture_name=self.name,
                detected=False,
                confidence=0.0,
                timestamp=timestamp,
                handedness=handedness,
            )

        # Calculate confidence
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
        non_thumb_fingers = [
            hand_analysis.index,
            hand_analysis.middle,
            hand_analysis.ring,
            hand_analysis.pinky,
        ]

        # 1. Non-thumb curl completeness factor
        non_thumb_scores = []
        for f in non_thumb_fingers:
            if f.position == FingerPosition.CURLED:
                non_thumb_scores.append(1.0)
            elif f.position == FingerPosition.PARTIALLY_BENT:
                non_thumb_scores.append(0.65)
            else:
                non_thumb_scores.append(0.0)

        non_thumb_factor = sum(non_thumb_scores) / len(non_thumb_scores)

        # 2. Thumb factor
        thumb_pos = hand_analysis.thumb.position
        if thumb_pos == FingerPosition.CURLED:
            thumb_factor = 1.0
        elif thumb_pos == FingerPosition.PARTIALLY_BENT:
            thumb_factor = 0.85
        else:  # UNKNOWN
            thumb_factor = 0.70

        curl_factor = 0.80 * non_thumb_factor + 0.20 * thumb_factor

        # 3. Quality & Stability factor across all 5 fingers
        all_fingers = [hand_analysis.thumb] + non_thumb_fingers
        quality_stability = calculate_quality_and_stability(all_fingers)

        final_score = curl_factor * quality_stability
        return round(max(0.0, min(1.0, final_score)), 2)
