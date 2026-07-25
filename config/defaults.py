"""
gesturedrive.config.defaults
==============================
Hardcoded default values for every configuration key.

These constants serve two purposes:
1. The lowest-priority fallback when keys are missing from TOML files.
2. The source of truth for generating ``config/default.toml`` via the
   ``scripts/generate_default_config.py`` utility.

Rules
-----
- Every key that appears in the config schema MUST have a default here.
- No dynamic computation — plain literals only.
- Grouped by section to mirror the TOML structure.
"""

from __future__ import annotations

# ── [camera] ──────────────────────────────────────────────────────────────────
CAMERA_DEVICE_INDEX: int = 0
CAMERA_WIDTH: int = 1280
CAMERA_HEIGHT: int = 720
CAMERA_FPS: float = 30.0

# ── [tracking] ────────────────────────────────────────────────────────────────
TRACKING_MAX_NUM_HANDS: int = 2
TRACKING_MIN_DETECTION_CONFIDENCE: float = 0.70
TRACKING_MIN_TRACKING_CONFIDENCE: float = 0.50
TRACKING_MODEL_COMPLEXITY: int = 1

# ── [analysis] ────────────────────────────────────────────────────────────────
ANALYSIS_FINGER_EXTENDED_ANGLE: float = 155.0
ANALYSIS_FINGER_CURLED_ANGLE: float = 115.0
ANALYSIS_FINGER_HYSTERESIS_MARGIN: float = 10.0
ANALYSIS_THUMB_EXTENDED_ANGLE: float = 150.0
ANALYSIS_THUMB_CURLED_ANGLE: float = 120.0
ANALYSIS_HISTORY_SIZE: int = 6

# ── [gesture] ─────────────────────────────────────────────────────────────────
GESTURE_STEERING_SMOOTHING_ALPHA: float = 0.15
GESTURE_STEERING_DEADZONE: float = 0.05
GESTURE_STEERING_SENSITIVITY: float = 1.0
GESTURE_STEERING_CURVE_EXPONENT: float = 3.0
GESTURE_STEERING_MAX_ANGLE: float = 30.0
GESTURE_STEERING_AUTO_CENTER_RATE: float = 0.15
GESTURE_STEERING_PREFERRED_HAND: str = "right"
GESTURE_THROTTLE_DEADZONE: float = 0.05
GESTURE_BRAKE_Z_THRESHOLD: float = -0.10
GESTURE_HANDBRAKE_HOLD_FRAMES: int = 3
GESTURE_HORN_HOLD_FRAMES: int = 2
GESTURE_ACTIVATION_FRAMES: int = 3
GESTURE_COOLDOWN_SECONDS: float = 0.5
GESTURE_CONFIDENCE_THRESHOLD: float = 0.60
GESTURE_STABILITY_TIMEOUT: float = 0.5
GESTURE_PINCH_MAX_NORMALIZED_DISTANCE: float = 0.75
GESTURE_PINCH_MIN_CONFIDENCE: float = 0.45
GESTURE_PRIORITY_OPEN_PALM: int = 20
GESTURE_PRIORITY_POINT: int = 40
GESTURE_PRIORITY_PEACE: int = 50
GESTURE_PRIORITY_FIST: int = 60
GESTURE_PRIORITY_THUMBS_UP: int = 80
GESTURE_PRIORITY_PINCH: int = 90

# ── [controller] ──────────────────────────────────────────────────────────────
CONTROLLER_TYPE: str = "xbox"       # "xbox" | "null"
CONTROLLER_RUMBLE_ENABLED: bool = False
CONTROLLER_DEADZONE: float = 0.05
CONTROLLER_TRIGGER_MIN: int = 0
CONTROLLER_TRIGGER_MAX: int = 255
CONTROLLER_STICK_MIN: int = -32768
CONTROLLER_STICK_MAX: int = 32767
CONTROLLER_UPDATE_FREQUENCY: int = 60
XBOX_OUTPUT_RT_MAX: int = 255
XBOX_OUTPUT_LT_MAX: int = 255
XBOX_OUTPUT_STEERING_SENSITIVITY: float = 1.0
XBOX_OUTPUT_STEERING_INVERSION: bool = False
XBOX_OUTPUT_HANDBRAKE_BUTTON: str = "A"

# ── [active_game] ─────────────────────────────────────────────────────────────
ACTIVE_GAME_PLUGIN_ID: str = "forza_horizon"

# ── [active_profile] ──────────────────────────────────────────────────────────
ACTIVE_PROFILE_NAME: str = "default"

# ── [logging] ─────────────────────────────────────────────────────────────────
LOGGING_LEVEL: str = "INFO"
LOGGING_FILE: str = "logs/gesturedrive.log"
LOGGING_MAX_BYTES: int = 10_485_760   # 10 MB
LOGGING_BACKUP_COUNT: int = 5

# ── [diagnostics] ─────────────────────────────────────────────────────────────
DIAGNOSTICS_FPS_WINDOW_FRAMES: int = 60
DIAGNOSTICS_PERFORMANCE_INTERVAL_SECONDS: float = 5.0

# ── [calibration] ─────────────────────────────────────────────────────────────
CALIBRATION_COUNTDOWN_DURATION: float = 3.0
CALIBRATION_MIN_STEERING_RANGE: float = 10.0
CALIBRATION_MAX_ALLOWED_STEERING_RANGE: float = 90.0
CALIBRATION_FILE_LOCATION: str = "profiles/default_calibration.json"
CALIBRATION_REQUIRED_FRAMES_PER_STEP: int = 30
CALIBRATION_MIN_MOVEMENT_THRESHOLD: float = 10.0
CALIBRATION_STABLE_HOLD_DURATION: float = 0.6
CALIBRATION_SUCCESS_MESSAGE_DURATION: float = 1.2
CALIBRATION_INSTRUCTION_DISPLAY_DURATION: float = 1.0
CALIBRATION_VALIDATION_TIMEOUT: float = 15.0
CALIBRATION_REVIEW_SCREEN_DURATION: float = 30.0
CALIBRATION_CAMERA_MIRRORED: bool = True
CALIBRATION_TRANSITION_PAUSE_DURATION: float = 1.5
CALIBRATION_TRANSITION_COUNTDOWN_DURATION: float = 3.0
CALIBRATION_MAX_CENTER_TOLERANCE: float = 3.0


