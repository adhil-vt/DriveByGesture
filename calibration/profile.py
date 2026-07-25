"""
gesturedrive.calibration.profile
==================================
CalibrationProfile: stores per-user gesture baselines.

This dataclass is the output of a completed CalibrationSession and the
primary input for gesture recognizers and InputMapper normalization.

It is serialized to JSON by ProfileStorage alongside the UserProfile.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from core.models import Vector3


@dataclass
class CalibrationProfile:
    """
    Per-user hand pose baselines captured during calibration.

    All angle values are in degrees. All ratios are in [0.0, 1.0].

    Attributes
    ----------
    neutral_palm_normal:
        The palm's normal vector (facing direction) when the hand is in
        the neutral driving position. Used as the zero-reference for steering.
    max_left_angle:
        Maximum steering-left angle recorded during calibration (degrees).
    max_right_angle:
        Maximum steering-right angle recorded during calibration (degrees).
    throttle_open_ratio:
        Finger curl ratio when the hand is fully open (minimum throttle).
    throttle_closed_ratio:
        Finger curl ratio when the hand is fully closed (maximum throttle).
    brake_z_threshold:
        Palm centroid Z-depth below which brake is considered active.
    handedness_preference:
        Which hand to use for primary gesture input.
        One of: ``"left"``, ``"right"``, ``"any"``.
    captured_at:
        UTC datetime when this profile was created.
    profile_version:
        Schema version for forward-compatibility checking.
    """

    neutral_palm_normal: Optional[Vector3] = None
    max_left_angle: float = 45.0
    max_right_angle: float = 45.0
    throttle_open_ratio: float = 1.0
    throttle_closed_ratio: float = 0.0
    brake_z_threshold: float = -0.10
    handedness_preference: str = "right"
    captured_at: datetime = field(default_factory=datetime.utcnow)
    profile_version: int = 1

    def is_complete(self) -> bool:
        """
        Return True if all required baseline values have been captured.

        A profile is incomplete if any required field is still at its
        default/None value from a partial calibration session.
        """
        return self.neutral_palm_normal is not None
