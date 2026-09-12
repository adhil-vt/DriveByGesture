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

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Mapping

from config import defaults as D


@dataclass
class CameraConfig:
    """Configuration for the webcam input source."""

    device_index: int = D.CAMERA_DEVICE_INDEX
    width: int = D.CAMERA_WIDTH
    height: int = D.CAMERA_HEIGHT
    fps: float = D.CAMERA_FPS
    mirror_preview: bool = True
    overlay_enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None = None) -> CameraConfig:
        payload = dict(data or {})
        return cls(
            device_index=int(payload.get("device_index", D.CAMERA_DEVICE_INDEX)),
            width=int(payload.get("width", D.CAMERA_WIDTH)),
            height=int(payload.get("height", D.CAMERA_HEIGHT)),
            fps=float(payload.get("fps", D.CAMERA_FPS)),
            mirror_preview=bool(payload.get("mirror_preview", True)),
            overlay_enabled=bool(payload.get("overlay_enabled", True)),
        )


@dataclass
class TrackingConfig:
    """Configuration for the MediaPipe hand tracker."""

    max_num_hands: int = D.TRACKING_MAX_NUM_HANDS
    min_detection_confidence: float = D.TRACKING_MIN_DETECTION_CONFIDENCE
    min_tracking_confidence: float = D.TRACKING_MIN_TRACKING_CONFIDENCE
    model_complexity: int = D.TRACKING_MODEL_COMPLEXITY

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None = None) -> TrackingConfig:
        payload = dict(data or {})
        return cls(
            max_num_hands=int(payload.get("max_num_hands", D.TRACKING_MAX_NUM_HANDS)),
            min_detection_confidence=float(
                payload.get("min_detection_confidence", D.TRACKING_MIN_DETECTION_CONFIDENCE)
            ),
            min_tracking_confidence=float(
                payload.get("min_tracking_confidence", D.TRACKING_MIN_TRACKING_CONFIDENCE)
            ),
            model_complexity=int(payload.get("model_complexity", D.TRACKING_MODEL_COMPLEXITY)),
        )


@dataclass
class AnalysisConfig:
    """Configuration for finger state analysis, thresholds, and temporal filtering."""

    finger_extended_angle: float = D.ANALYSIS_FINGER_EXTENDED_ANGLE
    finger_curled_angle: float = D.ANALYSIS_FINGER_CURLED_ANGLE
    finger_hysteresis_margin: float = D.ANALYSIS_FINGER_HYSTERESIS_MARGIN
    thumb_extended_angle: float = D.ANALYSIS_THUMB_EXTENDED_ANGLE
    thumb_curled_angle: float = D.ANALYSIS_THUMB_CURLED_ANGLE
    history_size: int = D.ANALYSIS_HISTORY_SIZE

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None = None) -> AnalysisConfig:
        payload = dict(data or {})
        return cls(
            finger_extended_angle=float(payload.get("finger_extended_angle", D.ANALYSIS_FINGER_EXTENDED_ANGLE)),
            finger_curled_angle=float(payload.get("finger_curled_angle", D.ANALYSIS_FINGER_CURLED_ANGLE)),
            finger_hysteresis_margin=float(
                payload.get("finger_hysteresis_margin", D.ANALYSIS_FINGER_HYSTERESIS_MARGIN)
            ),
            thumb_extended_angle=float(payload.get("thumb_extended_angle", D.ANALYSIS_THUMB_EXTENDED_ANGLE)),
            thumb_curled_angle=float(payload.get("thumb_curled_angle", D.ANALYSIS_THUMB_CURLED_ANGLE)),
            history_size=int(payload.get("history_size", D.ANALYSIS_HISTORY_SIZE)),
        )


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
    steering_inversion: bool = False
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

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None = None) -> GestureConfig:
        payload = dict(data or {})
        return cls(
            steering_smoothing_alpha=float(
                payload.get("steering_smoothing_alpha", D.GESTURE_STEERING_SMOOTHING_ALPHA)
            ),
            steering_deadzone=float(payload.get("steering_deadzone", D.GESTURE_STEERING_DEADZONE)),
            steering_sensitivity=float(payload.get("steering_sensitivity", D.GESTURE_STEERING_SENSITIVITY)),
            steering_curve_exponent=float(
                payload.get("steering_curve_exponent", D.GESTURE_STEERING_CURVE_EXPONENT)
            ),
            max_steering_angle=float(payload.get("max_steering_angle", D.GESTURE_STEERING_MAX_ANGLE)),
            steering_auto_center_rate=float(
                payload.get("steering_auto_center_rate", D.GESTURE_STEERING_AUTO_CENTER_RATE)
            ),
            steering_preferred_hand=str(payload.get("steering_preferred_hand", D.GESTURE_STEERING_PREFERRED_HAND)),
            steering_inversion=bool(payload.get("steering_inversion", False)),
            throttle_deadzone=float(payload.get("throttle_deadzone", D.GESTURE_THROTTLE_DEADZONE)),
            brake_z_threshold=float(payload.get("brake_z_threshold", D.GESTURE_BRAKE_Z_THRESHOLD)),
            handbrake_hold_frames=int(payload.get("handbrake_hold_frames", D.GESTURE_HANDBRAKE_HOLD_FRAMES)),
            horn_hold_frames=int(payload.get("horn_hold_frames", D.GESTURE_HORN_HOLD_FRAMES)),
            activation_frames=int(payload.get("activation_frames", D.GESTURE_ACTIVATION_FRAMES)),
            cooldown_seconds=float(payload.get("cooldown_seconds", D.GESTURE_COOLDOWN_SECONDS)),
            confidence_threshold=float(payload.get("confidence_threshold", D.GESTURE_CONFIDENCE_THRESHOLD)),
            stability_timeout=float(payload.get("stability_timeout", D.GESTURE_STABILITY_TIMEOUT)),
            pinch_max_normalized_distance=float(
                payload.get("pinch_max_normalized_distance", D.GESTURE_PINCH_MAX_NORMALIZED_DISTANCE)
            ),
            pinch_min_confidence=float(payload.get("pinch_min_confidence", D.GESTURE_PINCH_MIN_CONFIDENCE)),
            priority_open_palm=int(payload.get("priority_open_palm", D.GESTURE_PRIORITY_OPEN_PALM)),
            priority_point=int(payload.get("priority_point", D.GESTURE_PRIORITY_POINT)),
            priority_peace=int(payload.get("priority_peace", D.GESTURE_PRIORITY_PEACE)),
            priority_fist=int(payload.get("priority_fist", D.GESTURE_PRIORITY_FIST)),
            priority_thumbs_up=int(payload.get("priority_thumbs_up", D.GESTURE_PRIORITY_THUMBS_UP)),
            priority_pinch=int(payload.get("priority_pinch", D.GESTURE_PRIORITY_PINCH)),
        )


@dataclass
class ControllerConfig:
    """Configuration for the virtual controller output."""

    emulation_type: str = D.CONTROLLER_TYPE
    rumble_enabled: bool = D.CONTROLLER_RUMBLE_ENABLED
    deadzone: float = D.CONTROLLER_DEADZONE
    trigger_min: int = D.CONTROLLER_TRIGGER_MIN
    trigger_max: int = D.CONTROLLER_TRIGGER_MAX
    stick_min: int = D.CONTROLLER_STICK_MIN
    stick_max: int = D.CONTROLLER_STICK_MAX
    update_frequency: int = D.CONTROLLER_UPDATE_FREQUENCY

    def __init__(
        self,
        emulation_type: str | None = None,
        type: str | None = None,
        rumble_enabled: bool = D.CONTROLLER_RUMBLE_ENABLED,
        deadzone: float = D.CONTROLLER_DEADZONE,
        trigger_min: int = D.CONTROLLER_TRIGGER_MIN,
        trigger_max: int = D.CONTROLLER_TRIGGER_MAX,
        stick_min: int = D.CONTROLLER_STICK_MIN,
        stick_max: int = D.CONTROLLER_STICK_MAX,
        update_frequency: int = D.CONTROLLER_UPDATE_FREQUENCY,
    ) -> None:
        self.emulation_type = emulation_type if emulation_type is not None else (type if type is not None else D.CONTROLLER_TYPE)
        self.rumble_enabled = rumble_enabled
        self.deadzone = deadzone
        self.trigger_min = trigger_min
        self.trigger_max = trigger_max
        self.stick_min = stick_min
        self.stick_max = stick_max
        self.update_frequency = update_frequency

    @property
    def type(self) -> str:
        return self.emulation_type

    @type.setter
    def type(self, value: str) -> None:
        self.emulation_type = value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "emulation_type": self.emulation_type,
            "type": self.emulation_type,
            "rumble_enabled": self.rumble_enabled,
            "deadzone": self.deadzone,
            "trigger_min": self.trigger_min,
            "trigger_max": self.trigger_max,
            "stick_min": self.stick_min,
            "stick_max": self.stick_max,
            "update_frequency": self.update_frequency,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None = None) -> ControllerConfig:
        payload = dict(data or {})
        return cls(
            emulation_type=str(payload.get("emulation_type", payload.get("type", D.CONTROLLER_TYPE))),
            rumble_enabled=bool(payload.get("rumble_enabled", D.CONTROLLER_RUMBLE_ENABLED)),
            deadzone=float(payload.get("deadzone", D.CONTROLLER_DEADZONE)),
            trigger_min=int(payload.get("trigger_min", D.CONTROLLER_TRIGGER_MIN)),
            trigger_max=int(payload.get("trigger_max", D.CONTROLLER_TRIGGER_MAX)),
            stick_min=int(payload.get("stick_min", D.CONTROLLER_STICK_MIN)),
            stick_max=int(payload.get("stick_max", D.CONTROLLER_STICK_MAX)),
            update_frequency=int(payload.get("update_frequency", D.CONTROLLER_UPDATE_FREQUENCY)),
        )


@dataclass
class XboxOutputConfig:
    """Configuration for Xbox Output Plugin."""

    rt_max: int = D.XBOX_OUTPUT_RT_MAX
    lt_max: int = D.XBOX_OUTPUT_LT_MAX
    steering_sensitivity: float = D.XBOX_OUTPUT_STEERING_SENSITIVITY
    steering_inversion: bool = D.XBOX_OUTPUT_STEERING_INVERSION
    handbrake_button: str = D.XBOX_OUTPUT_HANDBRAKE_BUTTON

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None = None) -> XboxOutputConfig:
        payload = dict(data or {})
        return cls(
            rt_max=int(payload.get("rt_max", D.XBOX_OUTPUT_RT_MAX)),
            lt_max=int(payload.get("lt_max", D.XBOX_OUTPUT_LT_MAX)),
            steering_sensitivity=float(
                payload.get("steering_sensitivity", D.XBOX_OUTPUT_STEERING_SENSITIVITY)
            ),
            steering_inversion=bool(payload.get("steering_inversion", D.XBOX_OUTPUT_STEERING_INVERSION)),
            handbrake_button=str(payload.get("handbrake_button", D.XBOX_OUTPUT_HANDBRAKE_BUTTON)),
        )


@dataclass
class ActiveGameConfig:
    """Which game plugin to activate on startup."""

    plugin_id: str = D.ACTIVE_GAME_PLUGIN_ID

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None = None) -> ActiveGameConfig:
        payload = dict(data or {})
        return cls(plugin_id=str(payload.get("plugin_id", D.ACTIVE_GAME_PLUGIN_ID)))


@dataclass
class ProfileConfig:
    """Which user profile to load on startup."""

    name: str = D.ACTIVE_PROFILE_NAME

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None = None) -> ProfileConfig:
        payload = dict(data or {})
        return cls(name=str(payload.get("name", D.ACTIVE_PROFILE_NAME)))


ActiveProfileConfig = ProfileConfig


@dataclass
class GeneralConfig:
    """General application preference configuration."""

    auto_save_calibration: bool = True
    auto_start_pipeline: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None = None) -> GeneralConfig:
        payload = dict(data or {})
        return cls(
            auto_save_calibration=bool(payload.get("auto_save_calibration", True)),
            auto_start_pipeline=bool(payload.get("auto_start_pipeline", False)),
        )


@dataclass
class LoggingConfig:
    """Logging subsystem configuration."""

    level: str = D.LOGGING_LEVEL
    file: str = D.LOGGING_FILE
    max_bytes: int = D.LOGGING_MAX_BYTES
    backup_count: int = D.LOGGING_BACKUP_COUNT

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None = None) -> LoggingConfig:
        payload = dict(data or {})
        return cls(
            level=str(payload.get("level", D.LOGGING_LEVEL)),
            file=str(payload.get("file", D.LOGGING_FILE)),
            max_bytes=int(payload.get("max_bytes", D.LOGGING_MAX_BYTES)),
            backup_count=int(payload.get("backup_count", D.LOGGING_BACKUP_COUNT)),
        )


@dataclass
class DiagnosticsConfig:
    """Diagnostics and monitoring configuration."""

    fps_window_frames: int = D.DIAGNOSTICS_FPS_WINDOW_FRAMES
    performance_interval_seconds: float = D.DIAGNOSTICS_PERFORMANCE_INTERVAL_SECONDS

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None = None) -> DiagnosticsConfig:
        payload = dict(data or {})
        return cls(
            fps_window_frames=int(payload.get("fps_window_frames", D.DIAGNOSTICS_FPS_WINDOW_FRAMES)),
            performance_interval_seconds=float(
                payload.get("performance_interval_seconds", D.DIAGNOSTICS_PERFORMANCE_INTERVAL_SECONDS)
            ),
        )


@dataclass
class CalibrationConfig:
    """Calibration wizard configuration settings."""

    countdown_duration: float = D.CALIBRATION_COUNTDOWN_DURATION
    min_steering_range: float = D.CALIBRATION_MIN_STEERING_RANGE
    max_allowed_steering_range: float = D.CALIBRATION_MAX_ALLOWED_STEERING_RANGE
    calibration_file_location: str = D.CALIBRATION_FILE_LOCATION
    required_frames_per_step: int = D.CALIBRATION_REQUIRED_FRAMES_PER_STEP

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None = None) -> CalibrationConfig:
        payload = dict(data or {})
        return cls(
            countdown_duration=float(payload.get("countdown_duration", D.CALIBRATION_COUNTDOWN_DURATION)),
            min_steering_range=float(payload.get("min_steering_range", D.CALIBRATION_MIN_STEERING_RANGE)),
            max_allowed_steering_range=float(
                payload.get("max_allowed_steering_range", D.CALIBRATION_MAX_ALLOWED_STEERING_RANGE)
            ),
            calibration_file_location=str(
                payload.get("calibration_file_location", D.CALIBRATION_FILE_LOCATION)
            ),
            required_frames_per_step=int(
                payload.get("required_frames_per_step", D.CALIBRATION_REQUIRED_FRAMES_PER_STEP)
            ),
        )


@dataclass
class DesktopConfig:
    """Desktop mode configuration and gesture bindings."""

    mode: str = "driving"
    cursor_sensitivity: float = 1.75
    cursor_smoothing: float = 0.25
    cursor_deadzone: float = 0.05
    invert_x: bool = False
    invert_y: bool = False
    cursor_enabled: bool = True
    click_delay: float = 0.20
    scroll_speed: float = 1.0
    gesture_cooldown: float = 0.30
    repeat_delay: float = 0.50
    cursor_acceleration: bool = True
    workspace_w_pct: float = 0.80
    workspace_h_pct: float = 0.80
    show_workspace_overlay: bool = True
    custom_shortcut: str = "ctrl+tab"
    bindings: Dict[str, str] = field(default_factory=dict)
    enabled_actions: Dict[str, bool] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None = None) -> DesktopConfig:
        payload = dict(data or {})
        return cls(
            mode=str(payload.get("mode", "driving")),
            cursor_sensitivity=float(payload.get("cursor_sensitivity", 1.75)),
            cursor_smoothing=float(payload.get("cursor_smoothing", 0.25)),
            cursor_deadzone=float(payload.get("cursor_deadzone", 0.05)),
            invert_x=bool(payload.get("invert_x", False)),
            invert_y=bool(payload.get("invert_y", False)),
            cursor_enabled=bool(payload.get("cursor_enabled", True)),
            click_delay=float(payload.get("click_delay", 0.20)),
            scroll_speed=float(payload.get("scroll_speed", 1.0)),
            gesture_cooldown=float(payload.get("gesture_cooldown", 0.30)),
            repeat_delay=float(payload.get("repeat_delay", 0.50)),
            cursor_acceleration=bool(payload.get("cursor_acceleration", True)),
            workspace_w_pct=float(payload.get("workspace_w_pct", 0.80)),
            workspace_h_pct=float(payload.get("workspace_h_pct", 0.80)),
            show_workspace_overlay=bool(payload.get("show_workspace_overlay", True)),
            custom_shortcut=str(payload.get("custom_shortcut", "ctrl+tab")),
            bindings=dict(payload.get("bindings", {})) if isinstance(payload.get("bindings", {}), dict) else {},
            enabled_actions=dict(payload.get("enabled_actions", {}))
            if isinstance(payload.get("enabled_actions", {}), dict)
            else {},
        )


@dataclass
class AppConfig:
    """
    Root configuration object for the entire GestureDrive application.

    Constructed by ConfigLoader and accessed via ConfigManager.
    All fields have defaults from config.defaults so the app can run
    without any user config file.
    """
    general: GeneralConfig = field(default_factory=GeneralConfig)
    camera: CameraConfig = field(default_factory=CameraConfig)
    tracking: TrackingConfig = field(default_factory=TrackingConfig)
    analysis: AnalysisConfig = field(default_factory=AnalysisConfig)
    gesture: GestureConfig = field(default_factory=GestureConfig)
    controller: ControllerConfig = field(default_factory=ControllerConfig)
    desktop: DesktopConfig = field(default_factory=DesktopConfig)
    active_game: ActiveGameConfig = field(default_factory=ActiveGameConfig)
    active_profile: ProfileConfig = field(default_factory=ProfileConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    diagnostics: DiagnosticsConfig = field(default_factory=DiagnosticsConfig)
    calibration: CalibrationConfig = field(default_factory=CalibrationConfig)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "general": self.general.to_dict(),
            "camera": self.camera.to_dict(),
            "tracking": self.tracking.to_dict(),
            "analysis": self.analysis.to_dict(),
            "gesture": self.gesture.to_dict(),
            "controller": self.controller.to_dict(),
            "desktop": self.desktop.to_dict(),
            "active_game": self.active_game.to_dict(),
            "active_profile": self.active_profile.to_dict(),
            "logging": self.logging.to_dict(),
            "diagnostics": self.diagnostics.to_dict(),
            "calibration": self.calibration.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None = None) -> AppConfig:
        payload = dict(data or {})
        return cls(
            general=GeneralConfig.from_dict(payload.get("general", {})),
            camera=CameraConfig.from_dict(payload.get("camera", {})),
            tracking=TrackingConfig.from_dict(payload.get("tracking", {})),
            analysis=AnalysisConfig.from_dict(payload.get("analysis", {})),
            gesture=GestureConfig.from_dict(payload.get("gesture", {})),
            controller=ControllerConfig.from_dict(payload.get("controller", {})),
            desktop=DesktopConfig.from_dict(payload.get("desktop", {})),
            active_game=ActiveGameConfig.from_dict(payload.get("active_game", {})),
            active_profile=ProfileConfig.from_dict(payload.get("active_profile", {})),
            logging=LoggingConfig.from_dict(payload.get("logging", {})),
            diagnostics=DiagnosticsConfig.from_dict(payload.get("diagnostics", {})),
            calibration=CalibrationConfig.from_dict(payload.get("calibration", {})),
        )
