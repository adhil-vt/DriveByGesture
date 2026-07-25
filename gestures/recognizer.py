"""
gesturedrive.gestures.recognizer
================================
GestureRecognizer: backward-compatible wrapper around GestureManager.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from config.schema import GestureConfig
from analysis.finger_state import HandAnalysis
from gestures.gesture_result import GestureResult
from gestures.manager import ActiveGesture, GestureManager
from gestures.registry import GestureRegistry
from gestures.builtins.utils import extract_handedness

logger = logging.getLogger(__name__)


class GestureRecognizer:
    """
    Evaluates detected hand analyses using registered gestures.

    Delegates to GestureManager for conflict resolution, temporal stabilization,
    cooldown management, and confidence filtering.

    Parameters
    ----------
    registry: Optional[GestureRegistry]
        Registry containing gesture instances. If None, a new empty registry is created.
    config: Optional[GestureConfig]
        Configuration options for gesture stabilization, thresholds, and cooldowns.
        If None, default GestureConfig with activation_frames=1 is used for immediate recognition.
    """

    def __init__(
        self,
        registry: Optional[GestureRegistry] = None,
        config: Optional[GestureConfig] = None,
    ) -> None:
        self.registry = registry if registry is not None else GestureRegistry()
        if config is None:
            # Default to immediate single-frame recognition for raw recognizer calls
            self.config = GestureConfig(
                activation_frames=1,
                cooldown_seconds=0.0,
                confidence_threshold=0.0,
            )
        else:
            self.config = config

        self.manager = GestureManager(registry=self.registry, config=self.config)

    def recognize(self, hand_analyses: List[HandAnalysis]) -> List[GestureResult]:
        """
        Process hand analyses through GestureManager.

        Parameters
        ----------
        hand_analyses: List[HandAnalysis]
            List of hand analysis objects for the current frame.

        Returns
        -------
        List[GestureResult]
            List of gesture results.
        """
        return self.manager.process_hands(hand_analyses)

    def get_active_gesture(self, hand: str) -> ActiveGesture:
        """Return ActiveGesture state for the specified hand."""
        return self.manager.get_active_gesture(hand)

    def get_debug_info(self) -> str:
        """Return debug information string."""
        return self.manager.get_debug_info()

    @staticmethod
    def _extract_handedness(hand_analysis: HandAnalysis) -> Optional[str]:
        """Backward-compatible helper for extracting handedness string representation."""
        return extract_handedness(hand_analysis)
