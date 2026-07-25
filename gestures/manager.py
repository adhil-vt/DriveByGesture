"""
gesturedrive.gestures.manager
=============================
GestureManager: Real-time gesture management system providing conflict resolution,
temporal stabilization, gesture cooldowns, confidence filtering, and per-hand state tracking.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from config.schema import GestureConfig
from analysis.finger_state import HandAnalysis
from gestures.gesture_result import GestureResult
from gestures.registry import GestureRegistry

logger = logging.getLogger(__name__)


@dataclass
class ActiveGesture:
    """
    State representation of the active gesture for a single hand.

    Attributes
    ----------
    hand: str
        Handedness identifier ("LEFT" or "RIGHT").
    current_gesture: str
        Currently active gesture name (e.g. "Fist", "Point", "Unknown").
    previous_gesture: str
        Previously active gesture name.
    activation_timestamp: float
        Unix timestamp when the current gesture became active.
    last_update_timestamp: float
        Unix timestamp of the most recent frame evaluation.
    confidence: float
        Confidence score of the active gesture in [0.0, 1.0].
    frames_stable: int
        Number of consecutive frames the active gesture has remained stable.
    cooldown_remaining: float
        Remaining cooldown duration in seconds before gesture transition is allowed.
    """

    hand: str
    current_gesture: str = "Unknown"
    previous_gesture: str = "Unknown"
    activation_timestamp: float = 0.0
    last_update_timestamp: float = 0.0
    confidence: float = 0.0
    frames_stable: int = 0
    cooldown_remaining: float = 0.0

    @property
    def is_cooldown_ready(self) -> bool:
        """True if the gesture cooldown period has elapsed."""
        return self.cooldown_remaining <= 0.0


class HandGestureTracker:
    """
    Per-hand state machine tracking temporal stabilization, cooldown enforcement,
    and active gesture transitions.
    """

    def __init__(self, hand: str, config: GestureConfig) -> None:
        self.hand = hand
        self._config = config

        self.current_gesture: str = "Unknown"
        self.previous_gesture: str = "Unknown"
        self.activation_timestamp: float = 0.0
        self.last_update_timestamp: float = 0.0
        self.confidence: float = 0.0

        self.candidate_gesture: str = "Unknown"
        self.candidate_count: int = 0
        self.cooldown_until: float = 0.0

    def update(
        self, candidate_name: str, candidate_confidence: float, timestamp: float
    ) -> ActiveGesture:
        """
        Update the hand gesture state machine for the current frame.

        Parameters
        ----------
        candidate_name: str
            Name of the winning gesture candidate for the current frame.
        candidate_confidence: float
            Confidence score of the winning candidate.
        timestamp: float
            Current frame timestamp in seconds.

        Returns
        -------
        ActiveGesture
            Updated active gesture state.
        """
        self.last_update_timestamp = timestamp
        cooldown_rem = max(0.0, self.cooldown_until - timestamp)

        # 1. Check Cooldown Lockout
        if cooldown_rem > 0.0:
            if candidate_name == self.current_gesture:
                self.confidence = candidate_confidence
                self.candidate_count += 1
            return self.get_active_state(timestamp)

        # 2. Temporal Stabilization
        if candidate_name == self.candidate_gesture:
            self.candidate_count += 1
        else:
            self.candidate_gesture = candidate_name
            self.candidate_count = 1

        # 3. Activation Check
        if self.candidate_count >= self._config.activation_frames:
            if candidate_name != self.current_gesture:
                self.previous_gesture = self.current_gesture
                self.current_gesture = candidate_name
                self.activation_timestamp = timestamp
                self.confidence = candidate_confidence
                if self._config.cooldown_seconds > 0.0:
                    self.cooldown_until = timestamp + self._config.cooldown_seconds
            else:
                self.confidence = candidate_confidence

        return self.get_active_state(timestamp)

    def get_active_state(self, timestamp: float = 0.0) -> ActiveGesture:
        """Return a snapshot of the current ActiveGesture state."""
        ts = timestamp if timestamp > 0.0 else self.last_update_timestamp
        cooldown_rem = max(0.0, self.cooldown_until - ts) if ts > 0.0 else 0.0
        frames_stable = (
            self.candidate_count if self.candidate_gesture == self.current_gesture else 0
        )
        return ActiveGesture(
            hand=self.hand,
            current_gesture=self.current_gesture,
            previous_gesture=self.previous_gesture,
            activation_timestamp=self.activation_timestamp,
            last_update_timestamp=self.last_update_timestamp,
            confidence=self.confidence,
            frames_stable=frames_stable,
            cooldown_remaining=round(cooldown_rem, 3),
        )


class GestureManager:
    """
    Real-time gesture management system.

    Responsibilities
    ----------------
    - Evaluates registered gestures against incoming HandAnalysis frames.
    - Resolves conflicts deterministically (Validity -> Priority -> Confidence).
    - Filters weak detections below configurable confidence threshold.
    - Applies temporal stabilization over consecutive frames.
    - Enforces configurable cooldown periods.
    - Tracks independent ActiveGesture state for LEFT and RIGHT hands.
    - Formats rich debug summaries for UI/console monitoring.
    """

    def __init__(
        self,
        registry: Optional[GestureRegistry] = None,
        config: Optional[GestureConfig] = None,
    ) -> None:
        self.registry = registry if registry is not None else GestureRegistry()
        self.config = config if config is not None else GestureConfig()
        self._trackers: Dict[str, HandGestureTracker] = {
            "LEFT": HandGestureTracker("LEFT", self.config),
            "RIGHT": HandGestureTracker("RIGHT", self.config),
        }

    def process_hands(self, hand_analyses: List[HandAnalysis]) -> List[GestureResult]:
        """
        Process a batch of detected hands and produce stabilized GestureResults.

        Parameters
        ----------
        hand_analyses: List[HandAnalysis]
            List of hand analysis results for all hands detected in the frame.

        Returns
        -------
        List[GestureResult]
            Stabilized gesture results corresponding 1-to-1 with input hand_analyses.
        """
        results: List[GestureResult] = []

        for hand_analysis in hand_analyses:
            handedness = self._extract_handedness(hand_analysis) or "RIGHT"
            handedness = handedness.upper()

            if handedness not in self._trackers:
                self._trackers[handedness] = HandGestureTracker(handedness, self.config)

            tracker = self._trackers[handedness]
            timestamp = getattr(hand_analysis, "timestamp", 0.0)

            # 1. Conflict Resolution (Per Frame Candidate)
            winner_res = self._resolve_conflict(hand_analysis)

            # 2. Temporal Stabilization & State Update
            candidate_name = winner_res.gesture_name if winner_res.detected else "Unknown"
            candidate_conf = winner_res.confidence if winner_res.detected else 0.0

            active_state = tracker.update(
                candidate_name=candidate_name,
                candidate_confidence=candidate_conf,
                timestamp=timestamp,
            )

            # 3. Build Stabilized GestureResult
            is_detected = active_state.current_gesture != "Unknown"
            stabilized_res = GestureResult(
                gesture_name=active_state.current_gesture,
                detected=is_detected,
                confidence=active_state.confidence if is_detected else 0.0,
                timestamp=timestamp,
                handedness=handedness,
            )
            results.append(stabilized_res)

        return results

    def get_active_gesture(self, hand: str) -> ActiveGesture:
        """
        Retrieve current ActiveGesture state for the given hand.

        Parameters
        ----------
        hand: str
            Handedness identifier ("LEFT" or "RIGHT").
        """
        hand_key = hand.upper()
        if hand_key in self._trackers:
            return self._trackers[hand_key].get_active_state()
        return ActiveGesture(hand=hand_key)

    def _resolve_conflict(self, hand_analysis: HandAnalysis) -> GestureResult:
        """
        Evaluate all enabled gestures and resolve conflicts deterministically.

        Selection criteria (in order):
        1. Validity: detected == True and confidence >= confidence_threshold.
        2. Priority: higher gesture priority takes precedence.
        3. Confidence: higher confidence breaks ties among equal-priority gestures.
        """
        timestamp = getattr(hand_analysis, "timestamp", 0.0)
        handedness = self._extract_handedness(hand_analysis)

        registered_gestures = self.registry.get_all()
        enabled_gestures = [g for g in registered_gestures if g.enabled]

        candidates: List[Tuple[GestureResult, int]] = []

        for gesture in enabled_gestures:
            try:
                res = gesture.recognize(hand_analysis)
                if (
                    res is not None
                    and res.detected
                    and res.confidence >= self.config.confidence_threshold
                ):
                    candidates.append((res, gesture.priority))
            except Exception as exc:
                logger.error("Error executing gesture '%s': %s", gesture.name, exc, exc_info=True)

        if not candidates:
            return GestureResult(
                gesture_name="Unknown",
                detected=False,
                confidence=0.0,
                timestamp=timestamp,
                handedness=handedness,
            )

        # Sort deterministically:
        # 1. Gesture Priority (descending)
        # 2. Confidence score (descending)
        candidates.sort(key=lambda c: (c[1], c[0].confidence), reverse=True)

        best_result, _ = candidates[0]
        return best_result

    def get_debug_info(self) -> str:
        """
        Format debug output showing gesture status for LEFT and RIGHT hands.
        """
        lines = []
        for hand in ["LEFT", "RIGHT"]:
            tracker = self._trackers.get(hand)
            if tracker:
                state = tracker.get_active_state()
                cooldown_str = (
                    "Ready"
                    if state.is_cooldown_ready
                    else f"{state.cooldown_remaining:.2f}s"
                )
                lines.append(f"{hand}")
                lines.append(f"Gesture: {state.current_gesture.upper()}")
                lines.append(f"Confidence: {state.confidence:.2f}")
                lines.append(f"Frames Stable: {state.frames_stable}")
                lines.append(f"Cooldown: {cooldown_str}")
            else:
                lines.append(f"{hand}")
                lines.append("Gesture: UNKNOWN")
                lines.append("Confidence: 0.00")
                lines.append("Frames Stable: 0")
                lines.append("Cooldown: Ready")

            if hand == "LEFT":
                lines.append("")
                lines.append("---------------------")
                lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _extract_handedness(hand_analysis: HandAnalysis) -> Optional[str]:
        """Extract handedness string representation from HandAnalysis."""
        if hasattr(hand_analysis, "hand_state") and hasattr(
            hand_analysis.hand_state, "handedness"
        ):
            h = hand_analysis.hand_state.handedness
            return h.name if hasattr(h, "name") else str(h)
        return None
