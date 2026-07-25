"""
gesturedrive.analysis.finger_state
====================================
Pure data models (value objects) representing finger state and hand analysis results.

Rules
-----
- All models are immutable (frozen dataclasses and enums).
- Plain data carriers with no analysis or inference logic.
- No external dependencies (MediaPipe, controller, etc.).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from tracking.hand_state import HandState


class FingerPosition(Enum):
    """
    Physical flexion state of an individual finger.

    Members
    -------
    UNKNOWN:
        Position cannot be determined (e.g. occluded landmarks).
    EXTENDED:
        Finger is fully straight / unbent.
    PARTIALLY_BENT:
        Finger is partially curled / mid-flexion.
    CURLED:
        Finger is fully folded into the palm.
    """
    UNKNOWN = auto()
    EXTENDED = auto()
    PARTIALLY_BENT = auto()
    CURLED = auto()


class FingerName(Enum):
    """
    Standard anatomical identifiers for human fingers.

    Members
    -------
    THUMB:
        Digit 1 (Thumb).
    INDEX:
        Digit 2 (Index / Pointer finger).
    MIDDLE:
        Digit 3 (Middle finger).
    RING:
        Digit 4 (Ring finger).
    PINKY:
        Digit 5 (Little / Pinky finger).
    """
    THUMB = auto()
    INDEX = auto()
    MIDDLE = auto()
    RING = auto()
    PINKY = auto()


@dataclass(frozen=True)
class FingerState:
    """
    Flexion state and confidence of a single finger.

    Attributes
    ----------
    name:
        Which finger this state describes (THUMB, INDEX, MIDDLE, RING, PINKY).
    position:
        Current physical flexion position (EXTENDED, PARTIALLY_BENT, CURLED, UNKNOWN).
    confidence:
        Confidence score of the position classification in [0.0, 1.0].
    """
    name: FingerName
    position: FingerPosition
    confidence: float


@dataclass(frozen=True)
class HandAnalysis:
    """
    Aggregated finger state analysis for a single detected hand.

    Attributes
    ----------
    hand_state:
        The underlying HandState from the tracking subsystem.
    thumb:
        Flexion state of the thumb.
    index:
        Flexion state of the index finger.
    middle:
        Flexion state of the middle finger.
    ring:
        Flexion state of the ring finger.
    pinky:
        Flexion state of the pinky finger.
    timestamp:
        Timestamp of the frame/analysis in seconds.
    """
    hand_state: HandState
    thumb: FingerState
    index: FingerState
    middle: FingerState
    ring: FingerState
    pinky: FingerState
    timestamp: float
