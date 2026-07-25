"""
gesturedrive.calibration.config
===============================
CalibrationConfig: Configuration parameters for the Calibration Wizard subsystem.
"""

from __future__ import annotations

from dataclasses import dataclass
from config import defaults as D


@dataclass
class CalibrationConfig:
    """
    Configuration parameters for Calibration Wizard session and validation.

    Attributes
    ----------
    countdown_duration: float
        Duration of 3-2-1 countdown per capture step in seconds (default 3.0).
    min_steering_range: float
        Minimum steering angle displacement (left/right vs center) in degrees (default 10.0).
    max_allowed_steering_range: float
        Maximum allowed steering angle limit in degrees (default 90.0).
    calibration_file_location: str
        File path to save/load default calibration JSON (default "profiles/default_calibration.json").
    required_frames_per_step: int
        Number of valid hand tracking frames to collect per pose capture step (default 30).
    """
    countdown_duration: float = D.CALIBRATION_COUNTDOWN_DURATION
    min_steering_range: float = D.CALIBRATION_MIN_STEERING_RANGE
    max_allowed_steering_range: float = D.CALIBRATION_MAX_ALLOWED_STEERING_RANGE
    calibration_file_location: str = D.CALIBRATION_FILE_LOCATION
    required_frames_per_step: int = D.CALIBRATION_REQUIRED_FRAMES_PER_STEP
    min_movement_threshold: float = D.CALIBRATION_MIN_MOVEMENT_THRESHOLD
    stable_hold_duration: float = D.CALIBRATION_STABLE_HOLD_DURATION
    success_message_duration: float = D.CALIBRATION_SUCCESS_MESSAGE_DURATION
    instruction_display_duration: float = D.CALIBRATION_INSTRUCTION_DISPLAY_DURATION
    validation_timeout: float = D.CALIBRATION_VALIDATION_TIMEOUT
    review_screen_duration: float = D.CALIBRATION_REVIEW_SCREEN_DURATION
    camera_mirrored: bool = D.CALIBRATION_CAMERA_MIRRORED
    transition_pause_duration: float = D.CALIBRATION_TRANSITION_PAUSE_DURATION
    transition_countdown_duration: float = D.CALIBRATION_TRANSITION_COUNTDOWN_DURATION
