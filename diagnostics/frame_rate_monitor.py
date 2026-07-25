"""
gesturedrive.diagnostics.frame_rate_monitor
============================================
FPS tracker using a rolling window of frame timestamps.

Subscribes to FrameCapturedEvent and GestureRecognizedEvent to
independently track camera FPS and pipeline processing FPS.
"""

from __future__ import annotations

import collections
import logging
import time
from typing import Deque

logger = logging.getLogger(__name__)


class FrameRateMonitor:
    """
    Rolling-window FPS calculator.

    Maintains a fixed-size deque of timestamps. FPS is calculated as
    ``window_size / (newest_timestamp - oldest_timestamp)``.

    Parameters
    ----------
    window_frames:
        Number of frame timestamps to keep in the rolling window.
        Default 60 (gives stable FPS readings at 30 FPS over 2 seconds).
    label:
        Human-readable label for logging, e.g. ``"Camera"`` or ``"Pipeline"``.
    """

    def __init__(self, window_frames: int = 60, label: str = "FPS") -> None:
        self._window: Deque[float] = collections.deque(maxlen=window_frames)
        self._label = label

    def tick(self) -> None:
        """Record the current monotonic timestamp. Call once per frame."""
        self._window.append(time.monotonic())

    @property
    def fps(self) -> float:
        """
        Current frames per second.

        Returns 0.0 if fewer than 2 timestamps have been recorded.
        """
        if len(self._window) < 2:
            return 0.0
        elapsed = self._window[-1] - self._window[0]
        if elapsed <= 0.0:
            return 0.0
        return (len(self._window) - 1) / elapsed

    def reset(self) -> None:
        """Clear all recorded timestamps."""
        self._window.clear()
