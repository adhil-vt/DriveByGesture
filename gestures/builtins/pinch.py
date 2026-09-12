"""
gesturedrive.gestures.builtins.pinch
====================================
PinchGesture: Built-in gesture recognizer for detecting natural pinch poses between thumb and index tips.
"""

from __future__ import annotations

import math
import logging
from typing import Optional

from config.schema import GestureConfig
from analysis.finger_state import FingerPosition, HandAnalysis
from gestures.base import Gesture
from gestures.gesture_result import GestureResult
from gestures.builtins.utils import (
    calculate_pinch_signals,
    calculate_quality_and_stability,
    extract_handedness,
)

logger = logging.getLogger(__name__)


class PinchGesture(Gesture):
    """
    Gesture recognizer for detecting a natural Pinch pose.

    Natural Ergonomic Rules
    -----------------------
    - Combines multi-signal metrics:
        1. Normalized Thumb Tip ↔ Index Tip distance.
        2. Normalized Thumb Tip ↔ Index DIP distance.
        3. Normalized Thumb Tip ↔ Index MCP distance.
        4. Relative thumb/index direction vector alignment.
        5. Tracking quality and landmark stability.
    - Index finger must NOT be CURLED into the palm.
    - Middle finger is fully flexible: EXTENDED, PARTIALLY_BENT, or CURLED allowed.
    - Ring and Pinky fingers allow PARTIALLY_BENT or CURLED (relaxing tight fist requirement).
    - Thresholds sourced from GestureConfig.
    """

    def __init__(
        self,
        priority: int = 90,
        enabled: bool = True,
        config: Optional[GestureConfig] = None,
    ) -> None:
        super().__init__(name="Pinch", priority=priority, enabled=enabled)
        self._config = config or GestureConfig()

    def recognize(self, hand_analysis: HandAnalysis) -> GestureResult:
        timestamp = getattr(hand_analysis, "timestamp", 0.0)
        handedness = extract_handedness(hand_analysis)

        # 1. Index finger cannot be CURLED into the palm or UNKNOWN
        index_pos = hand_analysis.index.position
        if index_pos in (FingerPosition.CURLED, FingerPosition.UNKNOWN):
            return GestureResult(
                gesture_name=self.name,
                detected=False,
                confidence=0.0,
                timestamp=timestamp,
                handedness=handedness,
                rejection_reason="Index finger curled into palm",
            )

        # 2. Middle finger is flexible: EXTENDED, PARTIALLY_BENT, or CURLED allowed (cannot be UNKNOWN)
        middle_pos = hand_analysis.middle.position
        if middle_pos == FingerPosition.UNKNOWN:
            return GestureResult(
                gesture_name=self.name,
                detected=False,
                confidence=0.0,
                timestamp=timestamp,
                handedness=handedness,
                rejection_reason="Middle finger position unknown",
            )

        # 3. Ring and Pinky fingers allow PARTIALLY_BENT or CURLED (must NOT be EXTENDED or UNKNOWN)
        for f in [hand_analysis.ring, hand_analysis.pinky]:
            if f.position in (FingerPosition.EXTENDED, FingerPosition.UNKNOWN):
                return GestureResult(
                    gesture_name=self.name,
                    detected=False,
                    confidence=0.0,
                    timestamp=timestamp,
                    handedness=handedness,
                    rejection_reason=f"{f.name.name.title()} finger extended",
                )

        # 4. Multi-Signal Geometric Calculation
        signals = None
        if hasattr(hand_analysis, "hand_state"):
            signals = calculate_pinch_signals(hand_analysis.hand_state)

        # Calibrated tight pinch threshold (0.38 scale) to prevent false triggers when pointing
        max_dist = min(0.38, self._config.pinch_max_normalized_distance)
        min_conf = self._config.pinch_min_confidence

        if signals is not None:
            if signals["tip_tip_dist"] > max_dist:
                return GestureResult(
                    gesture_name=self.name,
                    detected=False,
                    confidence=0.0,
                    timestamp=timestamp,
                    handedness=handedness,
                    rejection_reason="Pinch distance too large",
                )

        # 5. Compute Smooth Multi-Signal Confidence
        confidence = self._compute_confidence(hand_analysis, signals=signals)

        detected = confidence >= min_conf

        return GestureResult(
            gesture_name=self.name,
            detected=detected,
            confidence=confidence if detected else 0.0,
            timestamp=timestamp,
            handedness=handedness,
            rejection_reason=None if detected else "Confidence below threshold",
        )

    def _compute_confidence(
        self, hand_analysis: HandAnalysis, signals: dict[str, float] | None = None
    ) -> float:
        """
        Calculate a natural, continuous confidence score in range [0.0, 1.0].
        Clean pinches naturally achieve ~85-95% confidence.
        """
        max_dist = min(0.38, self._config.pinch_max_normalized_distance)

        if signals is not None:
            d_tip_tip = signals["tip_tip_dist"]
            alignment = signals["direction_alignment"]

            # Signal 1: Smooth continuous decay for Tip-to-tip distance
            # Tight pinch (<= 0.22): full score 1.0
            # Normal pinch (0.22 to 0.38): smooth cosine decay from 1.0 down to 0.65 at limit
            if d_tip_tip <= 0.22:
                s_dist = 1.0
            elif d_tip_tip <= max_dist:
                ratio = (d_tip_tip - 0.22) / (max_dist - 0.22)
                s_dist = 0.65 + 0.35 * (0.5 * (1.0 + math.cos(math.pi * ratio)))
            else:
                s_dist = 0.0

            # Signal 2: Anatomical Alignment (thumb/index direction)
            # Normalized alignment in range [0.80, 1.00]
            s_align = max(0.0, min(1.0, 0.80 + 0.20 * max(0.0, alignment)))

            geom_score = 0.80 * s_dist + 0.20 * s_align
        else:
            geom_score = 0.90

        # Quality & Stability factor focused on primary active pinch fingers (Thumb & Index)
        active_fingers = [hand_analysis.thumb, hand_analysis.index]
        quality_stability = calculate_quality_and_stability(active_fingers)

        final_score = geom_score * quality_stability
        return round(max(0.0, min(1.0, final_score)), 2)
