"""
gesturedrive.actions.config
===========================
ActionEngineConfig: Configuration for ActionEngine steering normalization and gesture mappings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

from actions.action import ActionType


@dataclass
class ActionEngineConfig:
    """
    Configuration settings for ActionEngine.

    Attributes
    ----------
    max_steering_angle: float
        Maximum steering tilt angle in degrees (default 30.0).
    steering_deadzone: float
        Steering deadzone threshold in range [0.0, 1.0] (default 0.05).
    gesture_mappings: Dict[str, ActionType]
        Map of recognized gesture names (e.g. "Open Palm", "Fist", "Pinch") to ActionType.
    """
    max_steering_angle: float = 30.0
    steering_deadzone: float = 0.05
    steering_sensitivity: float = 1.0
    steering_curve_exponent: float = 1.0
    steering_ema_alpha: float = 1.0
    steering_auto_center_rate: float = 0.15
    steering_inversion: bool = False
    gesture_mappings: Dict[str, ActionType] = field(
        default_factory=lambda: {
            "OPEN PALM": ActionType.ACCELERATOR,
            "OPEN_PALM": ActionType.ACCELERATOR,
            "Open Palm": ActionType.ACCELERATOR,
            "FIST": ActionType.BRAKE,
            "Fist": ActionType.BRAKE,
            "PINCH": ActionType.HANDBRAKE,
            "Pinch": ActionType.HANDBRAKE,
        }
    )

