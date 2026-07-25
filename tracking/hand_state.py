"""
gesturedrive.tracking.hand_state
==================================
Immutable data models representing processed hand tracking data,
and TrackingService for event bus orchestration.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Tuple

from core.event_bus import EventBus
from core.events import ErrorEvent, FrameCapturedEvent, HandDetectedEvent
from core.exceptions import TrackingError
from core.interfaces import IHandTracker
from core.models import Handedness

logger = logging.getLogger(__name__)

_SOURCE_ID = "tracking.tracking_service"


@dataclass(frozen=True)
class Landmark:
    """
    A 3D normalized landmark point for a single hand joint.

    Attributes
    ----------
    id:
        Landmark index (0 to 20 per MediaPipe specification).
    x:
        Normalized horizontal position in [0.0, 1.0].
    y:
        Normalized vertical position in [0.0, 1.0].
    z:
        Depth relative to wrist landmark.
    """
    id: int
    x: float
    y: float
    z: float


@dataclass(frozen=True)
class BoundingBox:
    """
    2D bounding box encompassing all hand landmarks in normalized space.

    Attributes
    ----------
    left:
        Minimum x coordinate.
    top:
        Minimum y coordinate.
    right:
        Maximum x coordinate.
    bottom:
        Maximum y coordinate.
    width:
        Box width (right - left).
    height:
        Box height (bottom - top).
    """
    left: float
    top: float
    right: float
    bottom: float
    width: float
    height: float


@dataclass(frozen=True)
class HandState:
    """
    Complete processed state of a single detected hand.

    Attributes
    ----------
    handedness:
        Handedness classification (LEFT, RIGHT, or UNKNOWN).
    confidence:
        Detection/tracking confidence score in [0.0, 1.0].
    landmarks:
        List of 21 Landmark objects.
    bounding_box:
        BoundingBox enclosing the hand.
    palm_center:
        (x, y, z) average coordinate of palm landmarks (0, 1, 5, 9, 13, 17).
    hand_center:
        (x, y, z) average coordinate of all 21 landmarks.
    timestamp:
        Frame capture timestamp (Unix timestamp in seconds).
    """
    handedness: Handedness
    confidence: float
    landmarks: List[Landmark]
    bounding_box: BoundingBox
    palm_center: Tuple[float, float, float]
    hand_center: Tuple[float, float, float]
    timestamp: float = 0.0


class TrackingService:
    """
    Subscribes to ``FrameCapturedEvent``, processes frames through
    ``IHandTracker``, and publishes ``HandDetectedEvent``.
    """

    def __init__(self, tracker: IHandTracker, event_bus: EventBus) -> None:
        self._tracker = tracker
        self._bus = event_bus
        self._consecutive_errors: int = 0
        self._error_threshold: int = 10

    def register(self) -> None:
        """Subscribe to the EventBus. Call once during application startup."""
        self._bus.subscribe(FrameCapturedEvent, self.on_frame_captured)
        logger.info("TrackingService registered on EventBus.")

    def on_frame_captured(self, event: FrameCapturedEvent) -> None:
        """
        EventBus handler called for every captured frame.
        """
        try:
            hand_states: List[HandState] = self._tracker.process(event.frame)
            self._consecutive_errors = 0

            self._bus.publish(
                HandDetectedEvent(
                    source=_SOURCE_ID,
                    hand_state=hand_states,
                    hands_found=len(hand_states),
                )
            )
        except TrackingError as exc:
            self._consecutive_errors += 1
            logger.warning("TrackingError (frame %d): %s", event.frame.seq_id, exc)

            if self._consecutive_errors >= self._error_threshold:
                self._bus.publish(
                    ErrorEvent(
                        source=_SOURCE_ID,
                        error=exc,
                        severity="error",
                        user_message="Hand tracking is experiencing persistent errors.",
                    )
                )
