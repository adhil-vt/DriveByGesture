"""
gesturedrive.actions.action
===========================
ActionType enum and immutable Action model.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class ActionType(Enum):
    """
    High-level abstract action types supported by the Action Engine.
    """
    NONE = auto()
    ACCELERATOR = auto()
    BRAKE = auto()
    STEERING = auto()
    HANDBRAKE = auto()
    MOVE_CURSOR = auto()
    LEFT_CLICK = auto()
    RIGHT_CLICK = auto()
    DOUBLE_CLICK = auto()
    SCROLL = auto()


@dataclass(frozen=True)
class Action:
    """
    Immutable representation of an abstract action output.

    Attributes
    ----------
    action_type: ActionType
        Type of action (e.g. ACCELERATOR, BRAKE, STEERING, HANDBRAKE).
    value: float
        Action value/magnitude (typically [0.0, 1.0] or [-1.0, 1.0] for steering).
    confidence: float
        Confidence score of the recognized action in range [0.0, 1.0].
    """
    action_type: ActionType
    value: float = 1.0
    confidence: float = 1.0
