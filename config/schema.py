"""
gesturedrive.config.schema
============================
Typed configuration schema dataclasses.

Each section of the TOML config maps to one dataclass here.
AppConfig is the root object that contains all sections.

Implementation note
-------------------
These are standard Python dataclasses (no Pydantic dependency in v1).
Validation is performed by ConfigLoader after deserialization.
Pydantic can be adopted later for richer validation without changing
the schema interface — only ConfigLoader and schema.py change.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from config import defaults as D


@dataclass
class CameraConfig:
    """Configuration for the webcam input source."""
    device_index: int = D.CAMERA_DEVICE_INDEX
    width: int = D.CAMERA_WIDTH
    height: int = D.CAMERA_HEIGHT
    fps: float = D.CAMERA_FPS


@dataclass
class TrackingConfig:
    """Configuration for the MediaPipe hand tracker."""
    max_num_hands: int = D.TRACKING_MAX_NUM_HANDS
    min_detection_confidence: float = D.TRACKING_MIN_DETECTION_CONFIDENCE
    min_tracking_confidence: float = D.TRACKING_MIN_TRACKING_CONFIDENCE
    model_complexity: int = D.TRACKING_MODEL_COMPLEXITY


@dataclass
class AnalysisConfig:
    """Configuration for finger state analysis, thresholds, and temporal filtering."""
    finger_extended_angle: float = D.ANALYSIS_FINGER_EXTENDED_ANGLE
    finger_curled_angle: float = D.ANALYSIS_FINGER_CURLED_ANGLE
    finger_hysteresis_margin: float = D.ANALYSIS_FINGER_HYSTERESIS_MARGIN
    thumb_extended_angle: float = D.ANALYSIS_THUMB_EXTENDED_ANGLE
    thumb_curled_angle: float = D.ANALYSIS_THUMB_CURLED_ANGLE
    history_size: int = D.ANALYSIS_HISTORY_SIZE


@dataclass
class GestureConfig:
    """Configuration for the gesture recognition pipeline."""
    steering_smoothing_alpha: float = D.GESTURE_STEERING_SMOOTHING_ALPHA
    steering_deadzone: float = D.GESTURE_STEERING_DEADZONE
    steering_sensitivity: float = D.GESTURE_STEERING_SENSITIVITY
    steering_curve_exponent: float = D.GESTURE_STEERING_CURVE_EXPONENT
    max_steering_angle: float = D.GESTURE_STEERING_MAX_ANGLE
    steering_auto_center_rate: float = D.GESTURE_STEERING_AUTO_CENTER_RATE
    steering_preferred_hand: str = D.GESTURE_STEERING_PREFERRED_HAND
    throttle_deadzone: float = D.GESTURE_THROTTLE_DEADZONE
    brake_z_threshold: float = D.GESTURE_BRAKE_Z_THRESHOLD
    handbrake_hold_frames: int = D.GESTURE_HANDBRAKE_HOLD_FRAMES
    horn_hold_frames: int = D.GESTURE_HORN_HOLD_FRAMES
    activation_frames: int = D.GESTURE_ACTIVATION_FRAMES
    cooldown_seconds: float = D.GESTURE_COOLDOWN_SECONDS
    confidence_threshold: float = D.GESTURE_CONFIDENCE_THRESHOLD
    stability_timeout: float = D.GESTURE_STABILITY_TIMEOUT
    pinch_max_normalized_distance: float = D.GESTURE_PINCH_MAX_NORMALIZED_DISTANCE
    pinch_min_confidence: float = D.GESTURE_PINCH_MIN_CONFIDENCE
    priority_open_palm: int = D.GESTURE_PRIORITY_OPEN_PALM
    priority_point: int = D.GESTURE_PRIORITY_POINT
    priority_peace: int = D.GESTURE_PRIORITY_PEACE
    priority_fist: int = D.GESTURE_PRIORITY_FIST
    priority_thumbs_up: int = D.GESTURE_PRIORITY_THUMBS_UP
    priority_pinch: int = D.GESTURE_PRIORITY_PINCH


@dataclass
class ControllerConfig:
    """Configuration for the virtual controller output."""
    type: str = D.CONTROLLER_TYPE
    rumble_enabled: bool = D.CONTROLLER_RUMBLE_ENABLED
    deadzone: float = D.CONTROLLER_DEADZONE
    trigger_min: int = D.CONTROLLER_TRIGGER_MIN
    trigger_max: int = D.CONTROLLER_TRIGGER_MAX
    stick_min: int = D.CONTROLLER_STICK_MIN
    stick_max: int = D.CONTROLLER_STICK_MAX
    update_frequency: int = D.CONTROLLER_UPDATE_FREQUENCY


@dataclass
class XboxOutputConfig:
    """Configuration for Xbox Output Plugin."""
    rt_max: int = D.XBOX_OUTPUT_RT_MAX
    lt_max: int = D.XBOX_OUTPUT_LT_MAX
    steering_sensitivity: float = D.XBOX_OUTPUT_STEERING_SENSITIVITY
    steering_inversion: bool = D.XBOX_OUTPUT_STEERING_INVERSION
    handbrake_button: str = D.XBOX_OUTPUT_HANDBRAKE_BUTTON


@dataclass
class ActiveGameConfig:
    """Which game plugin to activate on startup."""
    plugin_id: str = D.ACTIVE_GAME_PLUGIN_ID


@dataclass
class ActiveProfileConfig:
    """Which user profile to load on startup."""
    name: str = D.ACTIVE_PROFILE_NAME


@dataclass
class LoggingConfig:
    """Logging subsystem configuration."""
    level: str = D.LOGGING_LEVEL
    file: str = D.LOGGING_FILE
    max_bytes: int = D.LOGGING_MAX_BYTES
    backup_count: int = D.LOGGING_BACKUP_COUNT


@dataclass
class DiagnosticsConfig:
    """Diagnostics and monitoring configuration."""
    fps_window_frames: int = D.DIAGNOSTICS_FPS_WINDOW_FRAMES
    performance_interval_seconds: float = D.DIAGNOSTICS_PERFORMANCE_INTERVAL_SECONDS


@dataclass
class CalibrationConfig:
    """Calibration wizard configuration settings."""
    countdown_duration: float = D.CALIBRATION_COUNTDOWN_DURATION
    min_steering_range: float = D.CALIBRATION_MIN_STEERING_RANGE
    max_allowed_steering_range: float = D.CALIBRATION_MAX_ALLOWED_STEERING_RANGE
    calibration_file_location: str = D.CALIBRATION_FILE_LOCATION
    required_frames_per_step: int = D.CALIBRATION_REQUIRED_FRAMES_PER_STEP


@dataclass
class AppConfig:
    """
    Root configuration object for the entire GestureDrive application.

    Constructed by ConfigLoader and accessed via ConfigManager.
    All fields have defaults from config.defaults so the app can run
    without any user config file.
    """
    camera: CameraConfig = field(default_factory=CameraConfig)
    tracking: TrackingConfig = field(default_factory=TrackingConfig)
    analysis: AnalysisConfig = field(default_factory=AnalysisConfig)
    gesture: GestureConfig = field(default_factory=GestureConfig)
    controller: ControllerConfig = field(default_factory=ControllerConfig)
    active_game: ActiveGameConfig = field(default_factory=ActiveGameConfig)
    active_profile: ActiveProfileConfig = field(default_factory=ActiveProfileConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    diagnostics: DiagnosticsConfig = field(default_factory=DiagnosticsConfig)
    calibration: CalibrationConfig = field(default_factory=CalibrationConfig)
