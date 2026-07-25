"""
gesturedrive.calibration.calibration_data
==========================================
CalibrationData: Dataclass storing personalized user steering calibration measurements.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict


def _get_utc_now_iso() -> str:
    """Return ISO format string for current UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


@dataclass
class CalibrationData:
    """
    Personalized steering baseline measurements for a user.

    Attributes
    ----------
    center_angle: float
        Hand tilt angle (degrees) when hand is held in neutral center position.
    left_limit: float
        Maximum comfortable left steering tilt angle (degrees).
    right_limit: float
        Maximum comfortable right steering tilt angle (degrees).
    maximum_left: float
        Absolute maximum left steering angle limit (degrees).
    maximum_right: float
        Absolute maximum right steering angle limit (degrees).
    calibration_date: str
        Timestamp ISO string when calibration was recorded.
    version: str
        Calibration data schema version string (default "1.0").
    """
    center_angle: float = 0.0
    left_limit: float = -30.0
    right_limit: float = 30.0
    maximum_left: float = -45.0
    maximum_right: float = 45.0
    calibration_date: str = field(default_factory=_get_utc_now_iso)
    version: str = "1.0"

    @property
    def left_range(self) -> float:
        """Angular span from center to left limit in degrees (positive quantity)."""
        return abs(self.center_angle - self.left_limit)

    @property
    def right_range(self) -> float:
        """Angular span from center to right limit in degrees (positive quantity)."""
        return abs(self.right_limit - self.center_angle)

    @property
    def total_range(self) -> float:
        """Total steering range span from left limit to right limit in degrees."""
        return self.left_range + self.right_range

    def is_valid(self, min_range: float = 5.0) -> bool:
        """Check if calibration range is valid (meets minimum range requirement)."""
        return self.left_range >= min_range and self.right_range >= min_range

    def to_dict(self) -> Dict[str, Any]:
        """Serialize calibration data to JSON-serializable dictionary."""
        return {
            "center_angle": self.center_angle,
            "left_limit": self.left_limit,
            "right_limit": self.right_limit,
            "maximum_left": self.maximum_left,
            "maximum_right": self.maximum_right,
            "calibration_date": self.calibration_date,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CalibrationData:
        """Construct CalibrationData from dictionary with safe key lookups."""
        return cls(
            center_angle=float(data.get("center_angle", 0.0)),
            left_limit=float(data.get("left_limit", -30.0)),
            right_limit=float(data.get("right_limit", 30.0)),
            maximum_left=float(data.get("maximum_left", -45.0)),
            maximum_right=float(data.get("maximum_right", 45.0)),
            calibration_date=str(data.get("calibration_date", _get_utc_now_iso())),
            version=str(data.get("version", "1.0")),
        )
