"""
gesturedrive.core.events
=========================
Immutable event dataclasses published on the EventBus.

Design rules
------------
- Every event is a frozen dataclass (immutable after creation).
- Events carry only data; no methods that mutate state.
- The ``source`` field identifies the publishing component for tracing.
- All cross-layer communication in GestureDrive flows through these events.

Event catalogue
---------------
FrameCapturedEvent          CaptureLoop → TrackingService
HandDetectedEvent           TrackingService → GestureService, UI
GestureRecognizedEvent      GestureService → ControllerService, UI
ControllerInputSentEvent    ControllerService → Diagnostics, UI
CalibrationCompleteEvent    CalibrationOrchestrator → ProfileManager, UI
ProfileChangedEvent         ProfileManager → ConfigManager, UI
ConfigChangedEvent          ConfigManager → all services
ErrorEvent                  Any component → GlobalErrorHandler, UI

Import note
-----------
CalibrationProfile, UserProfile, and InputProfile live outside core/ and
cannot be imported here (would break the one-way dependency rule).
Payload fields for those types are annotated as ``Any``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from core.models import (
    ControllerInput,
    Frame,
    GestureResultSet,
    HandState,
)


# ── Base ───────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class BaseEvent:
    """
    Common fields shared by every GestureDrive event.

    Attributes
    ----------
    source:     Dotted string identifying the publishing component,
                e.g. ``"input_capture.capture_loop"``.
    emitted_at: UTC datetime when the event was constructed.
    """
    source: str
    emitted_at: datetime = field(default_factory=datetime.utcnow)


# ── Camera layer ───────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class FrameCapturedEvent(BaseEvent):
    """
    Published by CaptureLoop each time a new camera frame is available.

    Subscribers: TrackingService, DiagnosticsPanel (FPS counter).
    """
    frame: Frame = field(default=None)  # type: ignore[assignment]


# ── Tracking layer ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class HandDetectedEvent(BaseEvent):
    """
    Published by TrackingService after MediaPipe processes a frame.

    Published even when no hands are detected so that downstream services
    can handle the "hands lost" case (e.g., reset controller to neutral).

    Subscribers: GestureService, PreviewPanel.
    """
    hand_state: HandState = field(default=None)  # type: ignore[assignment]
    hands_found: int = 0   # Convenience count: 0, 1, or 2


# ── Gesture layer ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class GestureRecognizedEvent(BaseEvent):
    """
    Published by GestureService after the GesturePipeline produces results.

    Subscribers: ControllerService, GesturePanel.
    """
    result_set: GestureResultSet = field(default=None)  # type: ignore[assignment]


# ── Controller layer ───────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ControllerInputSentEvent(BaseEvent):
    """
    Published by ControllerService after inputs are dispatched to vgamepad.

    Subscribers: DiagnosticsPanel, AxisGauge widget.
    """
    controller_input: ControllerInput = field(default=None)  # type: ignore[assignment]


# ── Calibration layer ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class CalibrationCompleteEvent(BaseEvent):
    """
    Published by CalibrationOrchestrator when a session completes
    successfully.

    Subscribers: ProfileManager (to persist the profile), UI (to dismiss
    the wizard and show confirmation).
    """
    profile: Any = None   # CalibrationProfile — typed as Any to avoid circular import


@dataclass(frozen=True)
class CalibrationStepChangedEvent(BaseEvent):
    """
    Published during calibration to update the wizard UI step indicator.

    Subscribers: CalibrationWizard.
    """
    step_index: int = 0
    step_name: str = ""
    total_steps: int = 0


# ── Profile layer ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ProfileChangedEvent(BaseEvent):
    """
    Published by ProfileManager when the active user profile is switched.

    Subscribers: ConfigManager, InputMapper (to reload CalibrationProfile),
    all UI panels (to refresh displayed name).
    """
    profile: Any = None   # UserProfile — typed as Any to avoid circular import


# ── Configuration layer ────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ConfigChangedEvent(BaseEvent):
    """
    Published by ConfigManager when a configuration value changes (including
    hot-reload from disk).

    Subscribers: Any service that reads from ConfigManager.
    """
    section: str = ""
    key: str = ""
    old_value: Any = None
    new_value: Any = None


# ── Error layer ────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ErrorEvent(BaseEvent):
    """
    Published by any component when a recoverable error occurs.

    The GlobalErrorHandler is always subscribed to this event.
    The UI status bar also subscribes to surface errors to the user.

    Attributes
    ----------
    error:          The original exception instance.
    severity:       ``"warning"``, ``"error"``, or ``"critical"``.
    user_message:   A human-readable description suitable for the UI.
    """
    error: Optional[Exception] = None
    severity: str = "error"   # "warning" | "error" | "critical"
    user_message: str = ""
