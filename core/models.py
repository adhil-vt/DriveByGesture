"""
gesturedrive.core.models
=========================
Pure data models (value objects) for GestureDrive.

Rules
-----
- All models are immutable where possible (frozen dataclasses).
- No business logic lives here — models are plain data carriers.
- All fields use Python built-ins or typing primitives only.
- No imports from any other gesturedrive package.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple


# ── Enumerations ───────────────────────────────────────────────────────────────

class Handedness(Enum):
    """Which hand MediaPipe detected."""
    LEFT = auto()
    RIGHT = auto()
    UNKNOWN = auto()


class GestureConfidence(Enum):
    """Coarse confidence band for a gesture result."""
    LOW = auto()       # < 0.5
    MEDIUM = auto()    # 0.5 – 0.79
    HIGH = auto()      # >= 0.80


# ── Primitive geometry ─────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Vector2(object):
    """A normalised 2-D point in [0.0, 1.0] image-space."""
    x: float
    y: float


@dataclass(frozen=True)
class Vector3(object):
    """A normalised 3-D point (z is depth relative to wrist)."""
    x: float
    y: float
    z: float


# ── Hand tracking models ───────────────────────────────────────────────────────

@dataclass(frozen=True)
class HandLandmarks:
    """
    The 21 MediaPipe hand landmark points for a single detected hand,
    stored as a list of normalised Vector3 coordinates.

    Index correspondence follows the MediaPipe Hands landmark map:
    https://developers.google.com/mediapipe/solutions/vision/hand_landmarker
    """
    points: Tuple[Vector3, ...]   # Exactly 21 elements
    handedness: Handedness
    confidence: float             # [0.0, 1.0]


@dataclass(frozen=True)
class HandState:
    """
    A snapshot of all hands detected in a single processed frame.

    Attributes
    ----------
    hands:      Up to 2 HandLandmarks objects (one per detected hand).
    timestamp:  Unix timestamp (seconds) when the source frame was captured.
    frame_seq:  Monotonically increasing sequence number from CaptureLoop.
    """
    hands: Tuple[HandLandmarks, ...]   # 0, 1, or 2 elements
    timestamp: float
    frame_seq: int


@dataclass(frozen=True)
class SteeringVector:
    """
    Decomposed palm orientation used by SteeringRecognizer.

    Attributes
    ----------
    angle:  Horizontal tilt in degrees (negative = left, positive = right).
    tilt:   Forward/backward lean in degrees.
    roll:   Clockwise/counter-clockwise roll in degrees.
    """
    angle: float
    tilt: float
    roll: float


# ── Frame model ────────────────────────────────────────────────────────────────

@dataclass
class Frame:
    """
    A single raw camera frame.

    Attributes
    ----------
    image:              The raw pixel data as a numpy ndarray (H×W×3, BGR).
                        Typed as ``object`` to avoid a numpy import in core/.
    timestamp:          Unix timestamp (seconds) at acquisition time.
    seq_id:             Monotonically increasing frame counter from CaptureLoop.
    width:              Frame width in pixels.
    height:             Frame height in pixels.
    capture_timestamp:  High-precision monotonic timestamp (seconds) at hardware acquisition.
    """
    image: object           # numpy.ndarray at runtime — kept as object here
    timestamp: float
    seq_id: int
    width: int
    height: int
    capture_timestamp: float = 0.0


# ── Gesture models ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class GestureResult:
    """
    The output of a single IGestureRecognizer for one frame.

    Attributes
    ----------
    gesture_name:   Unique string identifier, e.g. ``"steering"``.
    confidence:     Recognition confidence in [0.0, 1.0].
    value:          Continuous value for analog gestures (e.g., steering
                    angle in [-1.0, 1.0]).  ``None`` for boolean gestures.
    active:         ``True`` when the gesture is currently being performed.
    """
    gesture_name: str
    confidence: float
    value: Optional[float]
    active: bool


@dataclass
class GestureResultSet:
    """
    The aggregated output of GesturePipeline for a single HandState.

    Keyed by gesture_name for O(1) lookup by the InputMapper.
    """
    results: Dict[str, GestureResult] = field(default_factory=dict)
    timestamp: float = 0.0
    frame_seq: int = 0

    def get(self, gesture_name: str) -> Optional[GestureResult]:
        """Return the GestureResult for the given name, or None."""
        return self.results.get(gesture_name)

    def is_active(self, gesture_name: str) -> bool:
        """Return True if the named gesture is currently active."""
        result = self.results.get(gesture_name)
        return result.active if result is not None else False


# ── Controller models ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class AxisValues:
    """
    Normalised virtual gamepad axis values in [-1.0, 1.0].

    Attributes
    ----------
    left_stick_x:   Steering axis (left = -1.0, right = +1.0).
    left_stick_y:   Left stick vertical (unused in most racing games).
    right_stick_x:  Right stick horizontal (camera, if used).
    right_stick_y:  Right stick vertical (camera, if used).
    left_trigger:   Brake / reverse in [0.0, 1.0].
    right_trigger:  Throttle in [0.0, 1.0].
    """
    left_stick_x: float = 0.0
    left_stick_y: float = 0.0
    right_stick_x: float = 0.0
    right_stick_y: float = 0.0
    left_trigger: float = 0.0
    right_trigger: float = 0.0


@dataclass(frozen=True)
class ButtonState:
    """
    Snapshot of virtual gamepad digital button states.

    Each field is True when the button is pressed.
    """
    a: bool = False
    b: bool = False
    x: bool = False
    y: bool = False
    left_bumper: bool = False
    right_bumper: bool = False
    start: bool = False
    back: bool = False
    left_thumb: bool = False
    right_thumb: bool = False
    dpad_up: bool = False
    dpad_down: bool = False
    dpad_left: bool = False
    dpad_right: bool = False


@dataclass(frozen=True)
class ControllerInput:
    """
    A complete virtual controller snapshot sent to IVirtualController.

    Produced by InputMapper from a GestureResultSet.
    """
    axes: AxisValues
    buttons: ButtonState
    timestamp: float


# ── Input profile (used by game plugins & InputMapper) ─────────────────────────

@dataclass
class GestureAxisBinding:
    """
    Maps a named gesture to a controller axis with optional scaling.

    Attributes
    ----------
    gesture_name:   The gesture_name from GestureResult.
    axis_name:      The AxisValues field name this gesture drives.
    scale:          Multiplier applied after curve processing. Default 1.0.
    inverted:       If True, the gesture value is negated before mapping.
    deadzone:       Values within ±deadzone of zero are clamped to zero.
    """
    gesture_name: str
    axis_name: str
    scale: float = 1.0
    inverted: bool = False
    deadzone: float = 0.05


@dataclass
class GestureButtonBinding:
    """Maps a named boolean gesture to a single gamepad button."""
    gesture_name: str
    button_name: str


@dataclass
class InputProfile:
    """
    A game-specific controller mapping used by InputMapper.

    Provided by IGamePlugin.get_input_profile().
    """
    game_id: str
    axis_bindings: List[GestureAxisBinding] = field(default_factory=list)
    button_bindings: List[GestureButtonBinding] = field(default_factory=list)
    steering_curve_type: str = "linear"   # Plugin may override with its own curve name
