"""
gesturedrive.calibration
=========================
Per-user calibration subsystem.

Captures hand pose baselines that allow gesture recognizers to produce
accurate, user-normalized outputs regardless of hand size, lighting,
or webcam placement.
"""

from calibration.calibration_data import CalibrationData
from calibration.calibration_manager import CalibrationManager
from calibration.calibration_overlay import render_calibration_overlay
from calibration.calibration_session import CalibrationSession, CalibrationStep, StepSnapshot
from calibration.calibration_storage import CalibrationStorage
from calibration.config import CalibrationConfig

__all__ = [
    "CalibrationData",
    "CalibrationConfig",
    "CalibrationStorage",
    "CalibrationSession",
    "CalibrationStep",
    "StepSnapshot",
    "CalibrationManager",
    "render_calibration_overlay",
]
