"""
gesturedrive.tests.conftest
============================
Shared pytest fixtures for the entire test suite.

All fixtures use dependency injection; no fixture patches global state.
Hardware dependencies (camera, controller, mediapipe) are replaced with
mocks or stub implementations so tests run without any hardware present.
"""

from __future__ import annotations

import pytest

from controller.null_controller import NullController
from core.event_bus import EventBus
from core.models import (
    AxisValues,
    ButtonState,
    Frame,
    GestureResult,
    GestureResultSet,
    HandLandmarks,
    HandState,
    Handedness,
    Vector3,
)


# ── EventBus ──────────────────────────────────────────────────────────────────

@pytest.fixture
def event_bus() -> EventBus:
    """A fresh, empty EventBus for each test."""
    return EventBus()


# ── Controller ────────────────────────────────────────────────────────────────

@pytest.fixture
def null_controller() -> NullController:
    """A connected NullController with input logging enabled."""
    ctrl = NullController(log_inputs=True)
    ctrl.connect()
    return ctrl


# ── Frame fixtures ────────────────────────────────────────────────────────────

@pytest.fixture
def blank_frame() -> Frame:
    """A 640×480 blank frame with seq_id=1."""
    import numpy as np
    return Frame(
        image=np.zeros((480, 640, 3), dtype="uint8"),
        timestamp=1_000_000.0,
        seq_id=1,
        width=640,
        height=480,
    )


# ── Hand landmark fixtures ────────────────────────────────────────────────────

def _make_zero_landmarks(handedness: Handedness = Handedness.RIGHT) -> HandLandmarks:
    """21 zero-vector landmarks for a single hand."""
    points = tuple(Vector3(0.0, 0.0, 0.0) for _ in range(21))
    return HandLandmarks(points=points, handedness=handedness, confidence=0.95)


@pytest.fixture
def neutral_hand_state() -> HandState:
    """HandState with one right hand at the neutral (all-zero) position."""
    return HandState(
        hands=(_make_zero_landmarks(),),
        timestamp=1_000_000.0,
        frame_seq=1,
    )


@pytest.fixture
def no_hand_state() -> HandState:
    """HandState with no hands detected."""
    return HandState(hands=(), timestamp=1_000_000.0, frame_seq=1)


# ── Gesture result fixtures ───────────────────────────────────────────────────

@pytest.fixture
def neutral_gesture_result_set() -> GestureResultSet:
    """GestureResultSet representing a fully neutral driving state."""
    return GestureResultSet(
        results={
            "steering": GestureResult("steering", confidence=0.95, value=0.0, active=True),
            "throttle": GestureResult("throttle", confidence=0.90, value=0.0, active=False),
            "brake":    GestureResult("brake",    confidence=0.85, value=0.0, active=False),
        },
        timestamp=1_000_000.0,
        frame_seq=1,
    )
