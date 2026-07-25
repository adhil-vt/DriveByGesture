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
        """
        Analyze hand state and evaluate whether a natural Pinch gesture is performed.

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

        # 1. Index finger cannot be CURLED into the palm or UNKNOWN
        index_pos = hand_analysis.index.position
        if index_pos in (FingerPosition.CURLED, FingerPosition.UNKNOWN):
            return GestureResult(
                gesture_name=self.name,
                detected=False,
                confidence=0.0,
                timestamp=timestamp,
                handedness=handedness,
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
                )

        # 4. Multi-Signal Geometric Calculation
        signals = None
        if hasattr(hand_analysis, "hand_state"):
            signals = calculate_pinch_signals(hand_analysis.hand_state)

        max_dist = self._config.pinch_max_normalized_distance
        min_conf = self._config.pinch_min_confidence

        if signals is not None:
            # Check maximum distance threshold
            if signals["tip_tip_dist"] > max_dist:
                return GestureResult(
                    gesture_name=self.name,
                    detected=False,
                    confidence=0.0,
                    timestamp=timestamp,
                    handedness=handedness,
                )

        # 5. Compute Smooth Multi-Signal Confidence
        confidence = self._compute_confidence(hand_analysis, signals=signals)

        # Activate if smooth confidence >= min_confidence threshold
        detected = confidence >= min_conf

        return GestureResult(
            gesture_name=self.name,
            detected=detected,
            confidence=confidence if detected else 0.0,
            timestamp=timestamp,
            handedness=handedness,
        )

    def _compute_confidence(
        self, hand_analysis: HandAnalysis, signals: dict[str, float] | None = None
    ) -> float:
        """
        Calculate a smooth, continuous confidence score in range [0.0, 1.0].
        """
        max_dist = self._config.pinch_max_normalized_distance

        if signals is not None:
            d_tip_tip = signals["tip_tip_dist"]
            d_tip_dip = signals["tip_dip_dist"]
            d_tip_mcp = signals["tip_mcp_dist"]
            alignment = signals["direction_alignment"]

            # Signal 1: Tip-to-tip distance score (smooth fade calibrated for natural approach)
            if d_tip_tip <= 0.25:
                s1 = 1.0
            elif d_tip_tip <= max_dist:
                s1 = max(0.0, 1.0 - 0.55 * ((d_tip_tip - 0.25) / (max_dist - 0.25)))
            else:
                s1 = 0.0

            # Signal 2: Tip-to-DIP distance score
            if d_tip_dip <= 0.30:
                s2 = 1.0
            elif d_tip_dip <= 0.75:
                s2 = max(0.0, 1.0 - (d_tip_dip - 0.30) / 0.45)
            else:
                s2 = 0.0

            # Signal 3: Tip-to-MCP distance ratio (tip near DIP vs far at MCP)
            ratio = d_tip_dip / (d_tip_mcp + 1e-6)
            s3 = max(0.0, min(1.0, 1.0 - ratio * 0.60))

            # Signal 4: Relative direction vector alignment
            if d_tip_tip <= 0.25:
                s4 = 1.0
            else:
                s4 = max(0.0, min(1.0, 0.50 + 0.50 * alignment))

            geom_score = 0.45 * s1 + 0.25 * s2 + 0.15 * s3 + 0.15 * s4
        else:
            geom_score = 0.85

        # Signal 5: Quality & Stability factor across all 5 fingers
        all_fingers = [
            hand_analysis.thumb,
            hand_analysis.index,
            hand_analysis.middle,
            hand_analysis.ring,
            hand_analysis.pinky,
        ]
        quality_stability = calculate_quality_and_stability(all_fingers)

        final_score = geom_score * quality_stability
        return round(max(0.0, min(1.0, final_score)), 2)
