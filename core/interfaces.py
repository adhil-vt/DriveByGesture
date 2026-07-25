"""
gesturedrive.core.interfaces
=============================
Abstract Base Classes (ABCs) for every major component in GestureDrive.

Design rules
------------
- All ABCs live here; no concrete implementations.
- Concrete classes in their own packages implement these interfaces.
- High-level modules (GestureService, ControllerService, etc.) depend
  ONLY on these abstractions — never on concrete types.
- New implementations (e.g., a second camera backend, a PS5 controller)
  require ZERO changes to any existing code.

DIP: every dependency in the Application wiring graph is expressed as one
of these interfaces.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Iterator, List, Optional

from core.models import (
    ControllerInput,
    Frame,
    GestureResult,
    HandState,
    InputProfile,
)

# Any lives in calibration/profile.py (outside core/).
# It is referenced in ABCs as ``Any`` to preserve the one-way import rule.


# ── Camera / Capture ───────────────────────────────────────────────────────────

class ICameraSource(ABC):
    """
    Abstracts the physical or virtual camera device.

    Implementors
    ------------
    - ``input_capture.camera.OpenCVCameraSource`` (production)
    - A mock camera that replays recorded frames (testing)
    """

    @abstractmethod
    def open(self) -> None:
        """Open and initialise the camera device."""

    @abstractmethod
    def read(self) -> Frame:
        """
        Capture and return a single frame.

        Raises
        ------
        CaptureError
            If the frame cannot be read (e.g., device disconnected).
        """

    @abstractmethod
    def release(self) -> None:
        """Release the camera device and free all associated resources."""

    @property
    @abstractmethod
    def is_open(self) -> bool:
        """Return True if the camera device is currently open."""

    @property
    @abstractmethod
    def fps(self) -> float:
        """Configured frames-per-second for this camera source."""

    @property
    @abstractmethod
    def resolution(self) -> tuple[int, int]:
        """Return (width, height) of frames produced by this source."""


# ── Hand Tracking ──────────────────────────────────────────────────────────────

class IHandTracker(ABC):
    """
    Abstracts the hand-tracking model (MediaPipe Hands).

    Implementors
    ------------
    - ``tracking.hand_tracker.MediaPipeHandTracker`` (production)
    - A stub tracker that returns pre-recorded HandState objects (testing)
    """

    @abstractmethod
    def initialise(self) -> None:
        """
        Load model weights and prepare the tracker for processing.

        Raises
        ------
        TrackingError
            If model files are missing or the GPU/CPU context cannot be set up.
        """

    @abstractmethod
    def process(self, frame: Frame) -> List[HandState]:
        """
        Run inference on ``frame`` and return detected hand states.

        Parameters
        ----------
        frame:
            A raw camera frame from ICameraSource.

        Returns
        -------
        List[HandState]
            List of detected HandState objects for hands in the frame.
        """

    @abstractmethod
    def shutdown(self) -> None:
        """Release model resources."""


# ── Gesture Recognition ────────────────────────────────────────────────────────

class IGestureRecognizer(ABC):
    """
    Recognizes a single named gesture from a HandState.

    OCP: new gestures are added by creating a new class that implements this
    interface.  No existing recognizer is ever modified.

    Implementors
    ------------
    Anything in ``gesture/builtin/`` or ``gesture/custom/``.
    """

    @property
    @abstractmethod
    def gesture_name(self) -> str:
        """Unique identifier for this gesture, e.g. ``"steering"``."""

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name shown in the UI, e.g. ``"Steering"``."""

    @abstractmethod
    def recognize(
        self,
        hand_state: HandState,
        calibration: Optional[Any] = None,
    ) -> Optional[GestureResult]:
        """
        Attempt to recognize this gesture in ``hand_state``.

        Parameters
        ----------
        hand_state:
            Normalized landmarks for up to 2 detected hands.
        calibration:
            User-specific calibration baselines. May be ``None`` if the user
            has not yet completed calibration (recognizer must handle this).

        Returns
        -------
        GestureResult
            Recognition result including confidence and analog value.
        None
            If this gesture cannot be determined from the current hand state
            (e.g., relevant hand not detected).
        """


# ── Virtual Controller ─────────────────────────────────────────────────────────

class IVirtualController(ABC):
    """
    Abstracts the virtual gamepad device.

    Implementors
    ------------
    - ``controller.xbox_controller.XboxController`` (production via vgamepad)
    - ``controller.null_controller.NullController`` (safe mode / testing)
    """

    @abstractmethod
    def connect(self) -> None:
        """
        Create and register the virtual controller with the OS.

        Raises
        ------
        ControllerError
            If ViGEmBus is not installed or the device cannot be created.
        """

    @abstractmethod
    def apply(self, input_snapshot: ControllerInput) -> None:
        """
        Send a complete controller state snapshot to the virtual device.

        Parameters
        ----------
        input_snapshot:
            Fully computed axis values and button states.
        """

    @abstractmethod
    def reset(self) -> None:
        """Return all axes to center and release all buttons."""

    @abstractmethod
    def disconnect(self) -> None:
        """Unregister the virtual controller from the OS."""

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Return True if the virtual device is currently registered."""


# ── Game Plugin ────────────────────────────────────────────────────────────────

class IGamePlugin(ABC):
    """
    Encapsulates all game-specific controller mapping logic.

    OCP: adding a new game means creating a new class that implements this
    interface.  The Application and InputMapper never change.

    Plugin discovery: classes are registered via pyproject.toml entry points
    under the ``gesturedrive.games`` group.
    """

    @property
    @abstractmethod
    def game_id(self) -> str:
        """Unique machine-readable identifier, e.g. ``"forza_horizon"``."""

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable game title, e.g. ``"Forza Horizon 5"``."""

    @abstractmethod
    def get_input_profile(self) -> InputProfile:
        """
        Return the axis bindings, button bindings, and sensitivity curve
        configuration for this game.
        """

    @abstractmethod
    def on_activate(self) -> None:
        """Called when this plugin becomes the active game."""

    @abstractmethod
    def on_deactivate(self) -> None:
        """Called when this plugin is replaced by another."""


# ── Input Mapping ──────────────────────────────────────────────────────────────

class IInputMapper(ABC):
    """
    Translates a GestureResultSet into a ControllerInput.

    Depends on an InputProfile (from IGamePlugin) and a Any.
    """

    @abstractmethod
    def map(
        self,
        result_set,          # GestureResultSet — avoid import cycle
        calibration: Optional[Any],
        profile: InputProfile,
    ) -> ControllerInput:
        """
        Convert gesture data to controller input.

        Parameters
        ----------
        result_set:
            Active gestures and their values for the current frame.
        calibration:
            Per-user baselines used to normalise raw gesture values.
        profile:
            Game-specific axis/button bindings and curve configuration.

        Returns
        -------
        ControllerInput
            A fully resolved controller snapshot ready for IVirtualController.
        """


# ── Calibration ────────────────────────────────────────────────────────────────

class ICalibrator(ABC):
    """
    Orchestrates the multi-step calibration workflow.

    Implementors
    ------------
    - ``calibration.calibrator.CalibrationOrchestrator`` (production)
    - A stub calibrator that returns a fixed profile (testing)
    """

    @abstractmethod
    def start(self) -> None:
        """Begin the calibration sequence from step 0."""

    @abstractmethod
    def advance(self) -> None:
        """
        Confirm the current step and move to the next.

        Called by the UI when the user clicks "Next" in the wizard.
        """

    @abstractmethod
    def cancel(self) -> None:
        """Abort calibration without saving."""

    @property
    @abstractmethod
    def current_step(self) -> int:
        """Zero-based index of the calibration step currently in progress."""

    @property
    @abstractmethod
    def is_complete(self) -> bool:
        """True when all steps have been captured and validated."""
