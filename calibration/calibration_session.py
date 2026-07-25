"""
gesturedrive.calibration.calibration_session
=============================================
CalibrationSession: State machine driving step-by-step hand tilt calibration.
"""

from __future__ import annotations

import enum
import math
import statistics
import time
from dataclasses import dataclass
from typing import List, Optional, Sequence

from analysis.finger_state import HandAnalysis
from calibration.calibration_data import CalibrationData
from calibration.config import CalibrationConfig


class CalibrationStep(enum.Enum):
    NOT_STARTED = "not_started"
    CENTER = "center"
    LEFT = "left"
    RIGHT = "right"
    SUMMARY = "summary"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class StepSnapshot:
    """Snapshot data for current calibration step progress."""
    step: CalibrationStep
    instruction: str
    countdown_seconds: int
    live_angle: float
    captured_value: Optional[float]
    completion_ratio: float
    error_message: Optional[str] = None


class CalibrationSession:
    """
    Step-by-step state machine for capturing user steering angles.

    Parameters
    ----------
    config: Optional[CalibrationConfig]
        Calibration configuration settings.
    """

    def __init__(self, config: Optional[CalibrationConfig] = None) -> None:
        self.config = config or CalibrationConfig()

        self._step = CalibrationStep.NOT_STARTED
        self._step_start_time: float = 0.0
        self._samples: List[float] = []

        self._center_angle: Optional[float] = None
        self._left_limit: Optional[float] = None
        self._right_limit: Optional[float] = None

        self._error_message: Optional[str] = None
        self._last_live_angle: float = 0.0

    @property
    def current_step(self) -> CalibrationStep:
        return self._step

    @property
    def is_complete(self) -> bool:
        return self._step == CalibrationStep.COMPLETE

    @property
    def center_angle(self) -> Optional[float]:
        return self._center_angle

    @property
    def left_limit(self) -> Optional[float]:
        return self._left_limit

    @property
    def right_limit(self) -> Optional[float]:
        return self._right_limit

    @property
    def result_data(self) -> Optional[CalibrationData]:
        if (
            self._center_angle is None
            or self._left_limit is None
            or self._right_limit is None
        ):
            return None

        # Calculate limits relative to center
        max_left = self._left_limit - abs(self.config.max_allowed_steering_range)
        max_right = self._right_limit + abs(self.config.max_allowed_steering_range)

        return CalibrationData(
            center_angle=self._center_angle,
            left_limit=self._left_limit,
            right_limit=self._right_limit,
            maximum_left=max_left,
            maximum_right=max_right,
        )

    def start(self) -> None:
        """Begin calibration session at Step 1 (CENTER)."""
        self._center_angle = None
        self._left_limit = None
        self._right_limit = None
        self._transition_to(CalibrationStep.CENTER)

    def reset(self) -> None:
        """Reset entire session back to start."""
        self.start()

    def retry_step(self) -> None:
        """Retry current calibration step."""
        if self._step in (CalibrationStep.CENTER, CalibrationStep.LEFT, CalibrationStep.RIGHT):
            self._transition_to(self._step)
        elif self._step in (CalibrationStep.FAILED, CalibrationStep.SUMMARY):
            self.start()

    def accept_summary(self) -> bool:
        """User accepts the captured calibration summary."""
        if self._step == CalibrationStep.SUMMARY and self.result_data is not None:
            self._step = CalibrationStep.COMPLETE
            self._error_message = None
            return True
        return False

    def process_frame(
        self, hand_analyses: Optional[Sequence[HandAnalysis]], dt: float = 0.033
    ) -> StepSnapshot:
        """
        Process a single video frame during calibration.

        Parameters
        ----------
        hand_analyses: Optional[Sequence[HandAnalysis]]
            Hand analysis results for current frame.
        dt: float
            Elapsed frame delta time in seconds.

        Returns
        -------
        StepSnapshot
            Current snapshot of calibration state for overlay display.
        """
        if self._step in (CalibrationStep.NOT_STARTED, CalibrationStep.COMPLETE, CalibrationStep.SUMMARY, CalibrationStep.FAILED):
            return self._build_snapshot()

        # Check hand availability & error handling
        if not hand_analyses or len(hand_analyses) == 0:
            self._error_message = "No hand visible - please place hand in frame"
            return self._build_snapshot()

        if len(hand_analyses) > 1:
            self._error_message = "Multiple hands detected - show only 1 hand"
            return self._build_snapshot()

        self._error_message = None

        # Extract hand angle
        angle_deg = self._extract_angle(hand_analyses[0])
        self._last_live_angle = angle_deg

        # Collect sample
        self._samples.append(angle_deg)
        elapsed = time.monotonic() - self._step_start_time

        if elapsed >= self.config.countdown_duration or len(self._samples) >= self.config.required_frames_per_step:
            self._finish_current_step()

        return self._build_snapshot()

    def _extract_angle(self, analysis: HandAnalysis) -> float:
        """Extract hand tilt angle in degrees from hand landmarks."""
        state = getattr(analysis, "hand_state", None)
        if not state or not hasattr(state, "landmarks") or not state.landmarks or len(state.landmarks) < 21:
            return 0.0

        lms = state.landmarks
        wrist = lms[0]
        middle_mcp = lms[9]

        dx = middle_mcp.x - wrist.x
        dy = middle_mcp.y - wrist.y

        # In image space, y points down. Vector pointing up is (dx, -dy).
        angle_rad = math.atan2(dx, -dy)
        return math.degrees(angle_rad)

    def _transition_to(self, step: CalibrationStep) -> None:
        self._step = step
        self._step_start_time = time.monotonic()
        self._samples.clear()
        self._error_message = None

    def _finish_current_step(self) -> None:
        if not self._samples:
            captured_val = self._last_live_angle
        else:
            captured_val = statistics.median(self._samples)

        captured_val = round(captured_val, 2)

        if self._step == CalibrationStep.CENTER:
            self._center_angle = captured_val
            self._transition_to(CalibrationStep.LEFT)

        elif self._step == CalibrationStep.LEFT:
            self._left_limit = captured_val
            # Validate left movement range vs center
            if self._center_angle is not None and abs(self._center_angle - captured_val) < self.config.min_steering_range:
                self._error_message = "Steering range too small - Please rotate fully LEFT and retry."
                self._step = CalibrationStep.FAILED
                return
            self._transition_to(CalibrationStep.RIGHT)

        elif self._step == CalibrationStep.RIGHT:
            self._right_limit = captured_val
            # Validate right movement range vs center
            if self._center_angle is not None and abs(captured_val - self._center_angle) < self.config.min_steering_range:
                self._error_message = "Steering range too small - Please rotate fully RIGHT and retry."
                self._step = CalibrationStep.FAILED
                return
            self._transition_to(CalibrationStep.SUMMARY)

    def _build_snapshot(self) -> StepSnapshot:
        elapsed = time.monotonic() - self._step_start_time if self._step_start_time > 0 else 0.0
        countdown = max(0, int(math.ceil(self.config.countdown_duration - elapsed)))
        ratio = min(1.0, elapsed / max(0.01, self.config.countdown_duration))

        instruction = ""
        captured_val = None

        if self._step == CalibrationStep.CENTER:
            instruction = "Hold your hand naturally in the center."
            captured_val = self._center_angle
        elif self._step == CalibrationStep.LEFT:
            instruction = "Rotate your hand fully LEFT."
            captured_val = self._left_limit
        elif self._step == CalibrationStep.RIGHT:
            instruction = "Rotate your hand fully RIGHT."
            captured_val = self._right_limit
        elif self._step == CalibrationStep.SUMMARY:
            instruction = "Review summary and accept calibration."
            ratio = 1.0
        elif self._step == CalibrationStep.COMPLETE:
            instruction = "✓ Calibration Complete"
            ratio = 1.0
        elif self._step == CalibrationStep.FAILED:
            instruction = "Calibration failed. Please retry."
            ratio = 0.0

        return StepSnapshot(
            step=self._step,
            instruction=instruction,
            countdown_seconds=countdown,
            live_angle=round(self._last_live_angle, 2),
            captured_value=captured_val,
            completion_ratio=ratio,
            error_message=self._error_message,
        )
