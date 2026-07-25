"""
gesturedrive.gestures.base
==========================
Abstract Base Class for all gesture recognizers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from analysis.finger_state import HandAnalysis
    from gestures.gesture_result import GestureResult


class Gesture(ABC):
    """
    Abstract base class for individual gesture recognizers.

    Every concrete gesture class must inherit from this base class and implement
    the ``recognize`` method.

    Attributes
    ----------
    name: str
        Unique identifier for this gesture (e.g., "Fist", "Peace").
    priority: int
        Evaluation priority score. Higher values take precedence when multiple
        gestures are detected simultaneously.
    enabled: bool
        Whether this gesture is active and should be evaluated by the recognizer.
    """

    def __init__(self, name: str, priority: int = 0, enabled: bool = True) -> None:
        self._name = name
        self._priority = priority
        self._enabled = enabled

    @property
    def name(self) -> str:
        """Unique identifier for the gesture."""
        return self._name

    @property
    def priority(self) -> int:
        """Priority rank of the gesture (higher value = higher priority)."""
        return self._priority

    @priority.setter
    def priority(self, value: int) -> None:
        self._priority = value

    @property
    def enabled(self) -> bool:
        """State indicating whether this gesture is enabled."""
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value

    @abstractmethod
    def recognize(self, hand_analysis: HandAnalysis) -> GestureResult:
        """
        Analyze a single hand state and determine if this gesture is detected.

        Parameters
        ----------
        hand_analysis: HandAnalysis
            The finger positions and hand landmarks analysis for a single hand.

        Returns
        -------
        GestureResult
            The outcome of the gesture recognition attempt.
        """
        pass

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__}("
            f"name='{self.name}', "
            f"priority={self.priority}, "
            f"enabled={self.enabled})>"
        )
