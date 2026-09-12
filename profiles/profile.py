"""
gesturedrive.profiles.profile
================================
DriveProfile: self-contained per-profile configuration entity.

Replaces the old UserProfile stub that depended on the removed EventBus
architecture. Uses existing CalibrationData, GestureConfig, CameraConfig
directly without duplicating any backend logic.

Profile JSON format
-------------------
{
    "schema_version": 1,
    "name": "Forza Horizon 5",
    "description": "...",
    "game_name": "Forza Horizon 5",
    "author": "User",
    "created_at": "2026-07-26T00:00:00Z",
    "modified_at": "2026-07-26T00:00:00Z",
    "app_version": "1.0.0",
    "calibration": { ...CalibrationData.to_dict()... } | null,
    "steering": { "max_steering_angle": 30.0, ... },
    "camera": { "device_index": 0, "width": 640, "height": 480, "fps": 30.0 },
    "controller": { "steering_sensitivity": 1.0, "steering_inversion": false }
}
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Mapping, Optional

logger = logging.getLogger(__name__)

_APP_VERSION = "1.0.0"
_SCHEMA_VERSION = 1


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Metadata ───────────────────────────────────────────────────────────────────

@dataclass
class ProfileMetadata:
    """
    Human-readable identity and audit fields for a DriveProfile.

    All fields are optional except name — they default to sensible values
    so profiles can be created with a single name argument.
    """
    name: str
    description: str = ""
    game_name: str = ""
    author: str = "User"
    created_at: str = field(default_factory=_utc_iso)
    modified_at: str = field(default_factory=_utc_iso)
    app_version: str = _APP_VERSION

    def touch(self) -> None:
        """Update modified_at to current UTC time."""
        self.modified_at = _utc_iso()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "game_name": self.game_name,
            "author": self.author,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
            "app_version": self.app_version,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> ProfileMetadata:
        return cls(
            name=str(d.get("name", "Unnamed")),
            description=str(d.get("description", "")),
            game_name=str(d.get("game_name", "")),
            author=str(d.get("author", "User")),
            created_at=str(d.get("created_at", _utc_iso())),
            modified_at=str(d.get("modified_at", _utc_iso())),
            app_version=str(d.get("app_version", _APP_VERSION)),
        )


# ── Default sub-section dicts ──────────────────────────────────────────────────

def _default_steering() -> Dict[str, Any]:
    return {
        "max_steering_angle": 30.0,
        "steering_deadzone": 0.05,
        "steering_sensitivity": 1.0,
        "steering_smoothing_alpha": 0.15,
        "steering_curve_exponent": 3.0,
        "steering_inversion": False,
        "steering_auto_center_rate": 0.15,
        "steering_preferred_hand": "right",
        "throttle_deadzone": 0.05,
        "brake_z_threshold": -0.10,
        "handbrake_hold_frames": 3,
        "horn_hold_frames": 2,
        "activation_frames": 3,
        "cooldown_seconds": 0.5,
        "confidence_threshold": 0.60,
        "stability_timeout": 0.5,
        "pinch_max_normalized_distance": 0.75,
        "pinch_min_confidence": 0.45,
        "priority_open_palm": 20,
        "priority_point": 40,
        "priority_peace": 50,
        "priority_fist": 60,
        "priority_thumbs_up": 80,
        "priority_pinch": 90,
    }


def _default_camera() -> Dict[str, Any]:
    return {
        "device_index": 0,
        "width": 1280,
        "height": 720,
        "fps": 30.0,
        "mirror_preview": True,
        "overlay_enabled": True,
    }


def _default_controller() -> Dict[str, Any]:
    return {
        "emulation_type": "xbox",
        "rumble_enabled": False,
        "deadzone": 0.05,
        "trigger_min": 0,
        "trigger_max": 255,
        "stick_min": -32768,
        "stick_max": 32767,
        "update_frequency": 60,
    }


def _default_general() -> Dict[str, Any]:
    return {
        "auto_save_calibration": True,
        "auto_start_pipeline": False,
    }


def _default_desktop_bindings() -> Dict[str, str]:
    return {
        "Open Palm": "MOVE_CURSOR",
        "Pinch": "LEFT_CLICK",
        "Pinch Pinky": "RIGHT_CLICK",
        "Peace": "RIGHT_CLICK",
        "Point": "DOUBLE_CLICK",
        "Fist": "DRAG",
        "Thumbs Up": "VOLUME_UP",
        "Thumbs Down": "VOLUME_DOWN",
    }


def _default_enabled_actions() -> Dict[str, bool]:
    return {
        "MOVE_CURSOR": True,
        "LEFT_CLICK": True,
        "RIGHT_CLICK": True,
        "DOUBLE_CLICK": True,
        "DRAG": True,
        "SCROLL_UP": True,
        "SCROLL_DOWN": True,
        "VOLUME_UP": True,
        "VOLUME_DOWN": True,
        "MUTE": True,
        "PLAY_PAUSE": True,
        "NEXT_TRACK": True,
        "PREV_TRACK": True,
        "SHOW_DESKTOP": True,
        "TASK_VIEW": True,
        "CUSTOM_SHORTCUT": True,
    }


def _default_desktop() -> Dict[str, Any]:
    return {
        "mode": "driving",
        "cursor_sensitivity": 1.75,
        "cursor_smoothing": 0.25,
        "cursor_deadzone": 0.05,
        "invert_x": False,
        "invert_y": False,
        "cursor_enabled": True,
        "click_delay": 0.2,
        "scroll_speed": 1.0,
        "gesture_cooldown": 0.3,
        "repeat_delay": 0.5,
        "cursor_acceleration": True,
        "workspace_w_pct": 0.80,
        "workspace_h_pct": 0.80,
        "show_workspace_overlay": True,
        "bindings": _default_desktop_bindings(),
        "enabled_actions": _default_enabled_actions(),
        "custom_shortcut": "ctrl+tab",
    }


# ── DriveProfile ───────────────────────────────────────────────────────────────

@dataclass
class DriveProfile:
    """
    A single self-contained DriveByGesture profile.

    Encapsulates metadata, calibration snapshot, and all tunable settings.
    Uses CalibrationData.to_dict / from_dict for calibration serialization —
    no logic is duplicated here.

    Parameters
    ----------
    metadata: ProfileMetadata
        Identity and audit information.
    calibration: Optional[Dict[str, Any]]
        Raw calibration dict (from CalibrationData.to_dict()) or None if
        the user has not yet calibrated under this profile.
    steering: Dict[str, Any]
        Steering pipeline settings keys matching GestureConfig fields.
    camera: Dict[str, Any]
        Camera settings matching CameraConfig fields.
    controller: Dict[str, Any]
        Controller output settings.
    """
    metadata: ProfileMetadata
    calibration: Optional[Dict[str, Any]] = None
    steering: Dict[str, Any] = field(default_factory=_default_steering)
    camera: Dict[str, Any] = field(default_factory=_default_camera)
    controller: Dict[str, Any] = field(default_factory=_default_controller)
    general: Dict[str, Any] = field(default_factory=_default_general)
    desktop: Dict[str, Any] = field(default_factory=_default_desktop)

    # ── Convenience properties ────────────────────────────────────────────────

    @property
    def name(self) -> str:
        return self.metadata.name

    @property
    def is_calibrated(self) -> bool:
        """True when embedded calibration data is present and plausible."""
        if self.calibration is None:
            return False
        try:
            from calibration.calibration_data import CalibrationData
            data = CalibrationData.from_dict(self.calibration)
            return data.is_valid(min_range=5.0)
        except Exception:
            return False

    # ── Calibration helpers ───────────────────────────────────────────────────

    def get_calibration_data(self):
        """
        Return a CalibrationData object deserialized from the embedded dict.
        Returns None if no calibration data is stored.
        """
        if self.calibration is None:
            return None
        try:
            from calibration.calibration_data import CalibrationData
            return CalibrationData.from_dict(self.calibration)
        except Exception as exc:
            logger.warning("DriveProfile '%s': failed to parse calibration: %s", self.name, exc)
            return None

    def set_calibration_data(self, data) -> None:
        """
        Embed a CalibrationData object into this profile and touch metadata.
        Accepts CalibrationData instance or None to clear calibration.
        """
        if data is None:
            self.calibration = None
        else:
            self.calibration = data.to_dict()
        self.metadata.touch()

    def apply_gesture_config(self, gesture_config) -> None:
        """Snapshot a GestureConfig into this profile's steering section."""
        from config.schema import GestureConfig

        if isinstance(gesture_config, GestureConfig):
            data = gesture_config.to_dict()
        elif hasattr(gesture_config, "to_dict"):
            data = gesture_config.to_dict()
        elif isinstance(gesture_config, Mapping):
            data = GestureConfig.from_dict(gesture_config).to_dict()
        else:
            data = GestureConfig().to_dict()
        self.steering = data
        self.metadata.touch()

    def apply_camera_config(self, camera_config) -> None:
        """Snapshot a CameraConfig into this profile's camera section."""
        from config.schema import CameraConfig

        if isinstance(camera_config, CameraConfig):
            data = camera_config.to_dict()
        elif hasattr(camera_config, "to_dict"):
            data = camera_config.to_dict()
        elif isinstance(camera_config, Mapping):
            data = CameraConfig.from_dict(camera_config).to_dict()
        else:
            data = CameraConfig().to_dict()
        self.camera = data
        self.metadata.touch()

    def apply_controller_config(self, controller_config) -> None:
        """Snapshot a ControllerConfig into this profile's controller section."""
        from config.schema import ControllerConfig

        if isinstance(controller_config, ControllerConfig):
            data = controller_config.to_dict()
        elif hasattr(controller_config, "to_dict"):
            data = controller_config.to_dict()
        elif isinstance(controller_config, Mapping):
            data = ControllerConfig.from_dict(controller_config).to_dict()
        else:
            data = ControllerConfig().to_dict()
        self.controller = data
        self.metadata.touch()

    def apply_general_config(self, general_config) -> None:
        """Snapshot a general preferences mapping into this profile."""
        from config.schema import GeneralConfig

        if isinstance(general_config, GeneralConfig):
            data = general_config.to_dict()
        elif hasattr(general_config, "to_dict"):
            data = general_config.to_dict()
        elif isinstance(general_config, Mapping):
            data = GeneralConfig.from_dict(general_config).to_dict()
        else:
            data = GeneralConfig().to_dict()
        self.general = data
        self.metadata.touch()

    def apply_desktop_config(self, desktop_config) -> None:
        """Snapshot a DesktopConfig or desktop settings mapping into this profile."""
        from config.schema import DesktopConfig

        if isinstance(desktop_config, DesktopConfig):
            data = desktop_config.to_dict()
        elif hasattr(desktop_config, "to_dict"):
            data = desktop_config.to_dict()
        elif isinstance(desktop_config, Mapping):
            data = DesktopConfig.from_dict(desktop_config).to_dict()
        else:
            data = DesktopConfig().to_dict()
        self.desktop = data
        self.metadata.touch()

    # ── Serialization ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        """Serialize profile to a JSON-serializable dictionary."""
        d: Dict[str, Any] = {
            "schema_version": _SCHEMA_VERSION,
            **self.metadata.to_dict(),
            "calibration": self.calibration,
            "steering": dict(self.steering),
            "camera": dict(self.camera),
            "controller": dict(self.controller),
            "general": dict(self.general),
            "desktop": dict(self.desktop),
        }
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> DriveProfile:
        """Deserialize a DriveProfile from a dictionary. Tolerates missing keys."""
        from config.schema import CameraConfig, ControllerConfig, DesktopConfig, GestureConfig, GeneralConfig
        meta = ProfileMetadata.from_dict(d)
        return cls(
            metadata=meta,
            calibration=d.get("calibration"),
            steering=GestureConfig.from_dict(d.get("steering", {})).to_dict(),
            camera=CameraConfig.from_dict(d.get("camera", {})).to_dict(),
            controller=ControllerConfig.from_dict(d.get("controller", {})).to_dict(),
            general=GeneralConfig.from_dict(d.get("general", {})).to_dict(),
            desktop=DesktopConfig.from_dict(d.get("desktop", {})).to_dict(),
        )

    @classmethod
    def create_default(cls) -> DriveProfile:
        """Create a factory-fresh Default profile with no calibration."""
        return cls(metadata=ProfileMetadata(name="Default", description="Default DriveByGesture profile"))

    def __repr__(self) -> str:
        cal = "calibrated" if self.is_calibrated else "uncalibrated"
        return f"DriveProfile(name={self.name!r}, {cal})"
