"""
gesturedrive.tracking.landmark_filter
======================================
Adaptive One Euro Filter for 3D hand landmark stabilization.
"""

from __future__ import annotations

import math
import time
from typing import List, Optional

from tracking.hand_state import Landmark


class OneEuroFilter:
    """
    1D One Euro Filter for adaptive noise reduction and low-latency tracking.

    Parameters
    ----------
    min_cutoff: float
        Minimum cutoff frequency in Hz for low-velocity smoothing (default: 1.0).
    beta: float
        Speed coefficient for high-velocity responsiveness (default: 0.007).
    d_cutoff: float
        Cutoff frequency for the derivative filter in Hz (default: 1.0).
    """

    def __init__(
        self,
        min_cutoff: float = 1.0,
        beta: float = 0.007,
        d_cutoff: float = 1.0,
    ) -> None:
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff

        self._x_prev: Optional[float] = None
        self._dx_prev: float = 0.0
        self._t_prev: Optional[float] = None

    def reset(self) -> None:
        """Reset internal filter states."""
        self._x_prev = None
        self._dx_prev = 0.0
        self._t_prev = None

    def filter(self, x: float, timestamp: float) -> float:
        """
        Filter a scalar signal input x at time timestamp (in seconds).
        """
        if self._t_prev is None or self._x_prev is None:
            self._x_prev = x
            self._dx_prev = 0.0
            self._t_prev = timestamp
            return x

        dt = max(1e-4, timestamp - self._t_prev)
        self._t_prev = timestamp

        # Compute raw derivative & filtered derivative
        dx = (x - self._x_prev) / dt
        alpha_d = self._smoothing_factor(dt, self.d_cutoff)
        dx_hat = alpha_d * dx + (1.0 - alpha_d) * self._dx_prev
        self._dx_prev = dx_hat

        # Adaptive cutoff frequency
        cutoff = self.min_cutoff + self.beta * abs(dx_hat)
        alpha = self._smoothing_factor(dt, cutoff)

        x_hat = alpha * x + (1.0 - alpha) * self._x_prev
        self._x_prev = x_hat
        return x_hat

    @staticmethod
    def _smoothing_factor(dt: float, cutoff: float) -> float:
        r = 2.0 * math.pi * cutoff * dt
        return r / (r + 1.0)


class HandLandmarkFilter:
    """
    Applies OneEuroFilter to all 21 3D landmarks (x, y, z) of a detected hand.
    """

    def __init__(
        self,
        min_cutoff: float = 1.0,
        beta: float = 0.007,
        d_cutoff: float = 1.0,
    ) -> None:
        self._filters = [
            (
                OneEuroFilter(min_cutoff, beta, d_cutoff),
                OneEuroFilter(min_cutoff, beta, d_cutoff),
                OneEuroFilter(min_cutoff, beta, d_cutoff),
            )
            for _ in range(21)
        ]

    def reset(self) -> None:
        """Reset filters for all 21 landmarks."""
        for fx, fy, fz in self._filters:
            fx.reset()
            fy.reset()
            fz.reset()

    def filter_landmarks(
        self, landmarks: List[Landmark], timestamp: float
    ) -> List[Landmark]:
        """
        Apply OneEuroFilter to each landmark's (x, y, z) coordinates.
        """
        if len(landmarks) != 21:
            return landmarks

        filtered: List[Landmark] = []
        for i, lm in enumerate(landmarks):
            fx, fy, fz = self._filters[i]
            sx = fx.filter(lm.x, timestamp)
            sy = fy.filter(lm.y, timestamp)
            sz = fz.filter(lm.z, timestamp)
            filtered.append(
                Landmark(
                    id=lm.id,
                    x=max(0.0, min(1.0, sx)),
                    y=max(0.0, min(1.0, sy)),
                    z=sz,
                )
            )
        return filtered
