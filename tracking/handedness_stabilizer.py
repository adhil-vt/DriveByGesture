"""
gesturedrive.tracking.handedness_stabilizer
============================================
Temporal handedness stabilizer enforcing classification persistence across consecutive frames.
"""

from __future__ import annotations

import logging
from collections import deque
from typing import Deque, Optional, Tuple

from core.models import Handedness

logger = logging.getLogger(__name__)


class HandednessStabilizer:
    """
    Stabilizes MediaPipe handedness classification over time to prevent
    single-frame classification flips ("RIGHT" -> "LEFT" -> "RIGHT")
    and cold-start misclassification latching.

    Parameters
    ----------
    window_size: int
        Number of historical frames to retain for weighted voting (default: 7).
    switch_threshold: float
        Weighted confidence ratio required to switch active handedness (default: 0.65).
    min_confirm_frames: int
        Number of consecutive matching observations required to confirm initial handedness (default: 2).
    """

    def __init__(
        self,
        window_size: int = 7,
        switch_threshold: float = 0.65,
        min_confirm_frames: int = 2,
    ) -> None:
        self._window_size = window_size
        self._switch_threshold = switch_threshold
        self._min_confirm_frames = min_confirm_frames
        self._history: Deque[Tuple[Handedness, float]] = deque(maxlen=window_size)
        self._current_stabilized: Handedness = Handedness.UNKNOWN
        self._is_confirmed: bool = False

    def reset(self) -> None:
        """Clear temporal history and reset active classification."""
        self._history.clear()
        self._current_stabilized = Handedness.UNKNOWN
        self._is_confirmed = False

    @property
    def is_confirmed(self) -> bool:
        """True if initial handedness has been confirmed by matching consecutive frames."""
        return self._is_confirmed

    def update(
        self, raw_handedness: Handedness, raw_confidence: float
    ) -> Tuple[Handedness, float]:
        """
        Process incoming frame handedness and return stabilized Handedness and confidence.

        Parameters
        ----------
        raw_handedness: Handedness
            MediaPipe frame prediction (LEFT, RIGHT, UNKNOWN).
        raw_confidence: float
            MediaPipe prediction score in [0.0, 1.0].

        Returns
        -------
        Tuple[Handedness, float]
            (stabilized_handedness, aggregated_confidence)
        """
        if raw_handedness != Handedness.UNKNOWN:
            self._history.append((raw_handedness, max(0.1, raw_confidence)))

        if not self._history:
            return Handedness.UNKNOWN, 0.0

        weight_right = sum(conf for h, conf in self._history if h == Handedness.RIGHT)
        weight_left = sum(conf for h, conf in self._history if h == Handedness.LEFT)
        total_weight = weight_right + weight_left

        if total_weight <= 0.0:
            return self._current_stabilized, 0.0

        ratio_right = weight_right / total_weight
        ratio_left = weight_left / total_weight

        # 1. Cold-start confirmation phase (require min_confirm_frames consecutive matching frames)
        if not self._is_confirmed:
            if len(self._history) >= self._min_confirm_frames:
                recent = list(self._history)[-self._min_confirm_frames:]
                recent_h = [h for h, _ in recent]
                if all(h == Handedness.RIGHT for h in recent_h):
                    self._current_stabilized = Handedness.RIGHT
                    self._is_confirmed = True
                    avg_conf = sum(c for _, c in recent) / len(recent)
                    logger.debug(
                        "Handedness confirmed as RIGHT after %d matching frames.",
                        self._min_confirm_frames,
                    )
                    return self._current_stabilized, min(1.0, round(avg_conf, 3))
                elif all(h == Handedness.LEFT for h in recent_h):
                    self._current_stabilized = Handedness.LEFT
                    self._is_confirmed = True
                    avg_conf = sum(c for _, c in recent) / len(recent)
                    logger.debug(
                        "Handedness confirmed as LEFT after %d matching frames.",
                        self._min_confirm_frames,
                    )
                    return self._current_stabilized, min(1.0, round(avg_conf, 3))

            # Not yet confirmed: return the latest observation provisionally without locking
            latest_h, latest_c = self._history[-1]
            return latest_h, min(1.0, round(latest_c, 3))

        # 2. Hysteresis check for switching classification (once confirmed)
        if self._current_stabilized == Handedness.RIGHT:
            if ratio_left >= self._switch_threshold:
                logger.info(
                    "Handedness stabilized transition: RIGHT -> LEFT (ratio: %.2f)", ratio_left
                )
                self._current_stabilized = Handedness.LEFT
                avg_conf = weight_left / max(1, sum(1 for h, _ in self._history if h == Handedness.LEFT))
            else:
                avg_conf = weight_right / max(1, sum(1 for h, _ in self._history if h == Handedness.RIGHT))
        else:  # Currently LEFT
            if ratio_right >= self._switch_threshold:
                logger.info(
                    "Handedness stabilized transition: LEFT -> RIGHT (ratio: %.2f)", ratio_right
                )
                self._current_stabilized = Handedness.RIGHT
                avg_conf = weight_right / max(1, sum(1 for h, _ in self._history if h == Handedness.RIGHT))
            else:
                avg_conf = weight_left / max(1, sum(1 for h, _ in self._history if h == Handedness.LEFT))

        return self._current_stabilized, min(1.0, round(avg_conf, 3))

