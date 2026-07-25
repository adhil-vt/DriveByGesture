"""
gesturedrive.profiles.profile
================================
UserProfile dataclass: root entity for a user session.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from calibration.profile import CalibrationProfile


@dataclass
class UserProfile:
    """
    Represents a single user's complete GestureDrive configuration.

    Attributes
    ----------
    name:
        Unique display name for the profile (also used as the filename key).
    preferred_game_id:
        The game plugin ID to activate when this profile is loaded.
    calibration:
        Per-user hand pose baselines. None if calibration has not been run.
    created_at:
        UTC datetime when this profile was first created.
    last_used_at:
        UTC datetime of the most recent session using this profile.
    """
    name: str
    preferred_game_id: str = "forza_horizon"
    calibration: Optional[CalibrationProfile] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_used_at: Optional[datetime] = None

    @property
    def is_calibrated(self) -> bool:
        """True if this profile has a complete CalibrationProfile."""
        return (
            self.calibration is not None
            and self.calibration.is_complete()
        )
