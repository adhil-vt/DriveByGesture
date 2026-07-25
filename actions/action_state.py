"""
gesturedrive.actions.action_state
=================================
ActionState: Immutable aggregated snapshot of all active high-level actions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from actions.action import Action, ActionType


@dataclass(frozen=True)
class ActionState:
    """
    Aggregated state of abstract actions produced by ActionEngine for a single frame.

    Attributes
    ----------
    accelerator: bool
        True if ACCELERATOR action is active.
    brake: bool
        True if BRAKE action is active.
    handbrake: bool
        True if HANDBRAKE action is active.
    steering: float
        Normalized steering value in range [-1.0, 1.0] (Left = -1.0, Center = 0.0, Right = 1.0).
    active_actions: List[Action]
        List of all active Action objects for this frame.
    """
    accelerator: bool = False
    brake: bool = False
    handbrake: bool = False
    steering: float = 0.0
    active_actions: List[Action] = field(default_factory=list)
    raw_steering: float = 0.0
    steering_deadzone_active: bool = False
    steering_sensitivity: float = 1.0
    steering_curve_output: float = 0.0
    raw_sensor_angle: float = 0.0
    adjusted_steering_angle: float = 0.0

    def has_action(self, action_type: ActionType) -> bool:
        """Return True if an action of the given ActionType is present in active_actions."""
        return any(a.action_type == action_type for a in self.active_actions)

    def get_action(self, action_type: ActionType) -> Optional[Action]:
        """Return the active Action for the given ActionType, or None if inactive."""
        for a in self.active_actions:
            if a.action_type == action_type:
                return a
        return None
