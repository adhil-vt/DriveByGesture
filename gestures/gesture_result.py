"""
gesturedrive.gestures.gesture_result
====================================
Immutable data container representing the result of a gesture recognition evaluation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class GestureResult:
    """
    Immutable representation of a gesture recognition result for a single hand.

    Attributes
    ----------
    gesture_name: str
        The identifier of the gesture recognized (e.g., "Fist", "Open Palm", "Unknown").
    detected: bool
        True if the gesture was successfully detected, False otherwise.
    confidence: float
        Confidence score of the recognition in range [0.0, 1.0].
    timestamp: float
        Unix timestamp (in seconds) of the evaluated frame/hand state.
    handedness: Optional[str]
        Optional handedness of the hand ("Left", "Right", "UNKNOWN", etc.).
    """

    gesture_name: str
    detected: bool
    confidence: float
    timestamp: float
    handedness: Optional[str] = None
    rejection_reason: Optional[str] = None
