"""
gesturedrive.gestures.builtins.open_palm
=========================================
OpenPalmGesture: Built-in gesture recognizer for detecting an open palm pose.
"""

from __future__ import annotations

import logging

from analysis.finger_state import FingerPosition, HandAnalysis
from gestures.base import Gesture
from gestures.gesture_result import GestureResult
from gestures.builtins.utils import calculate_quality_and_stability, extract_handedness

logger = logging.getLogger(__name__)


class OpenPalmGesture(Gesture):
    """
    Gesture recognizer for detecting an Open Palm pose.

    Detection Rules
    ---------------
    - Index, Middle, Ring, and Pinky fingers must be EXTENDED (tolerating at most one PARTIALLY_BENT finger).
    - Thumb must be EXTENDED or PARTIALLY_BENT.
    - No finger may be CURLED or UNKNOWN.

    Confidence Calculation
    ----------------------
    - Evaluates extension completeness across all 5 fingers.
    - Factors in individual finger position confidence scores.
    - Penalizes overall confidence if fingers are partially bent, if finger confidences are low,
      or if hand landmark stability is low.
    """

    def __init__(self, priority: int = 10, enabled: bool = True) -> None:
        super().__init__(name="Open Palm", priority=priority, enabled=enabled)

    def recognize(self, hand_analysis: HandAnalysis) -> GestureResult:
        """
        Analyze hand state and evaluate whether an Open Palm gesture is performed.

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

        # Check for any invalid/curled states
        for f in fingers:
            if f.position in (FingerPosition.CURLED, FingerPosition.UNKNOWN):
                return GestureResult(
                    gesture_name=self.name,
                    detected=False,
                    confidence=0.0,
                    timestamp=timestamp,
                    handedness=handedness,
                )

        # Non-thumb fingers (Index, Middle, Ring, Pinky)
        non_thumb_fingers = [
            hand_analysis.index,
            hand_analysis.middle,
            hand_analysis.ring,
            hand_analysis.pinky,
        ]

        extended_count = sum(1 for f in non_thumb_fingers if f.position == FingerPosition.EXTENDED)
        partially_bent_count = sum(1 for f in non_thumb_fingers if f.position == FingerPosition.PARTIALLY_BENT)

        # Thumb rule: EXTENDED or PARTIALLY_BENT
        thumb_valid = hand_analysis.thumb.position in (FingerPosition.EXTENDED, FingerPosition.PARTIALLY_BENT)

        # Open palm requires thumb to be valid and at least 3 non-thumb fingers fully EXTENDED with at most 1 PARTIALLY_BENT
        if not (thumb_valid and extended_count >= 3 and partially_bent_count <= 1):
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
        fingers = [
            hand_analysis.thumb,
            hand_analysis.index,
            hand_analysis.middle,
            hand_analysis.ring,
            hand_analysis.pinky,
        ]

        # 1. Extension completeness factor
        ext_scores = []
        for f in fingers:
            if f.name.name == "THUMB":
                if f.position == FingerPosition.EXTENDED:
                    ext_scores.append(1.0)
                elif f.position == FingerPosition.PARTIALLY_BENT:
                    ext_scores.append(0.85)
                else:
                    ext_scores.append(0.0)
            else:
                if f.position == FingerPosition.EXTENDED:
                    ext_scores.append(1.0)
                elif f.position == FingerPosition.PARTIALLY_BENT:
                    ext_scores.append(0.70)
                else:
                    ext_scores.append(0.0)

        extension_factor = sum(ext_scores) / len(ext_scores)

        # 2. Quality & Stability factor across all 5 fingers
        quality_stability = calculate_quality_and_stability(fingers)

        final_score = extension_factor * quality_stability
        return round(max(0.0, min(1.0, final_score)), 2)
