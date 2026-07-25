"""
gesturedrive.gesture.pipeline
================================
GesturePipeline: runs all registered recognizers and aggregates results.

Design
------
- Receives a HandState and runs each IGestureRecognizer in registry order.
- Each recognizer runs in isolation: exceptions in one do not affect others.
- Returns a GestureResultSet containing all successful results.
- Does NOT publish events directly; the containing GestureService publishes.

GestureService is also defined here as the EventBus bridge that:
  1. Subscribes to HandDetectedEvent.
  2. Passes hand_state through GesturePipeline.
  3. Publishes GestureRecognizedEvent.
"""

from __future__ import annotations

import logging
from typing import Optional

from core.event_bus import EventBus
from core.events import ErrorEvent, GestureRecognizedEvent, HandDetectedEvent
from core.exceptions import GestureError
from core.models import CalibrationProfile, GestureResultSet, HandState
from gesture.registry import GestureRegistry

logger = logging.getLogger(__name__)

_SOURCE_ID = "gesture.pipeline"


class GesturePipeline:
    """
    Runs all recognizers from a GestureRegistry against a single HandState.

    Parameters
    ----------
    registry:
        A built ``GestureRegistry`` instance containing all active recognizers.

    Notes
    -----
    - Each recognizer call is wrapped in a try/except.  A failing recognizer
      logs a GestureError at ERROR level and its result is omitted from the
      GestureResultSet for that frame.
    - Recognizers returning ``None`` are silently skipped (not an error).
    """

    def __init__(self, registry: GestureRegistry) -> None:
        self._registry = registry

    def run(
        self,
        hand_state: HandState,
        calibration: Optional[CalibrationProfile] = None,
    ) -> GestureResultSet:
        """
        Execute all recognizers against ``hand_state``.

        Parameters
        ----------
        hand_state:
            Normalized landmarks for the current frame.
        calibration:
            Optional per-user calibration baselines passed through to
            each recognizer.

        Returns
        -------
        GestureResultSet
            Dict-keyed results for all gestures that produced output.
            Empty GestureResultSet if no recognizers produced a result.
        """
        result_set = GestureResultSet(
            timestamp=hand_state.timestamp,
            frame_seq=hand_state.frame_seq,
        )

        for recognizer in self._registry.all():
            try:
                result = recognizer.recognize(hand_state, calibration)
                if result is not None:
                    result_set.results[result.gesture_name] = result
            except Exception as exc:
                logger.error(
                    "Recognizer '%s' raised an exception: %s",
                    recognizer.gesture_name,
                    exc,
                    exc_info=True,
                )

        return result_set


class GestureService:
    """
    EventBus bridge: HandDetectedEvent → GesturePipeline → GestureRecognizedEvent.

    Parameters
    ----------
    pipeline:
        A configured GesturePipeline.
    event_bus:
        The application-wide EventBus.
    calibration:
        Optional CalibrationProfile injected at construction.
        Replaceable at runtime via ``set_calibration()``.
    """

    def __init__(
        self,
        pipeline: GesturePipeline,
        event_bus: EventBus,
        calibration: Optional[CalibrationProfile] = None,
    ) -> None:
        self._pipeline = pipeline
        self._bus = event_bus
        self._calibration = calibration

    def register(self) -> None:
        """Subscribe to the EventBus. Call once during application startup."""
        self._bus.subscribe(HandDetectedEvent, self.on_hand_detected)
        logger.info("GestureService registered on EventBus.")

    def set_calibration(self, calibration: Optional[CalibrationProfile]) -> None:
        """Replace the active calibration profile at runtime (e.g., on profile switch)."""
        self._calibration = calibration

    def on_hand_detected(self, event: HandDetectedEvent) -> None:
        """
        EventBus handler: process hand state through the pipeline and
        publish the gesture results.
        """
        result_set = self._pipeline.run(event.hand_state, self._calibration)

        self._bus.publish(
            GestureRecognizedEvent(
                source=_SOURCE_ID,
                result_set=result_set,
            )
        )
        # Also enqueue for async UI delivery (non-blocking)
        self._bus.publish_async(
            GestureRecognizedEvent(
                source=_SOURCE_ID,
                result_set=result_set,
            )
        )
