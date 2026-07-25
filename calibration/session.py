"""
gesturedrive.calibration.session
==================================
CalibrationSession: captures and aggregates landmark samples for one pose.

One CalibrationSession is created per calibration step. It collects a
fixed number of HandState frames, computes statistical baselines from
them, and returns the result to CalibrationOrchestrator.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from core.models import HandState

logger = logging.getLogger(__name__)


class CalibrationSession:
    """
    Captures N frames of a specific calibration pose and computes the
    statistical baseline for that pose.

    Parameters
    ----------
    pose_name:
        Human-readable name for this calibration step, e.g.
        ``"neutral_position"``. Used for logging and UI display.
    required_frames:
        Number of good frames to collect before the session is considered
        complete. Default: 90 (3 seconds at 30 FPS).
    min_confidence:
        Minimum MediaPipe detection confidence to accept a frame.
        Frames with lower confidence are discarded (not counted).

    Usage
    -----
        session = CalibrationSession("neutral_position")
        session.add_frame(hand_state)       # called per frame
        if session.is_complete:
            baseline = session.compute()    # returns computed baseline dict
    """

    def __init__(
        self,
        pose_name: str,
        required_frames: int = 90,
        min_confidence: float = 0.70,
    ) -> None:
        self._pose_name = pose_name
        self._required_frames = required_frames
        self._min_confidence = min_confidence
        self._frames: List[HandState] = []

    @property
    def pose_name(self) -> str:
        return self._pose_name

    @property
    def frames_captured(self) -> int:
        """Number of accepted frames collected so far."""
        return len(self._frames)

    @property
    def is_complete(self) -> bool:
        """True when required_frames have been captured."""
        return len(self._frames) >= self._required_frames

    @property
    def progress(self) -> float:
        """Capture progress as a fraction [0.0, 1.0]."""
        return min(1.0, len(self._frames) / self._required_frames)

    def add_frame(self, hand_state: HandState) -> bool:
        """
        Attempt to add a frame to the session buffer.

        Parameters
        ----------
        hand_state:
            The current frame's hand tracking result.

        Returns
        -------
        bool
            True if the frame was accepted (met confidence threshold).
            False if the frame was rejected (hand absent or low confidence).
        """
        raise NotImplementedError

    def compute(self) -> dict:
        """
        Compute statistical baselines from the collected frames.

        Must only be called after ``is_complete`` is True.

        Returns
        -------
        dict
            Key-value pairs representing the computed baseline for this pose.
            Keys correspond to CalibrationProfile fields.

        Raises
        ------
        RuntimeError
            If called before the session has captured enough frames.
        """
        raise NotImplementedError

    def reset(self) -> None:
        """Discard all captured frames and restart the session."""
        self._frames.clear()
