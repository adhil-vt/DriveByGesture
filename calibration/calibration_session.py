"""
gesturedrive.calibration.calibration_session
=============================================
CalibrationSession: State machine driving step-by-step hand tilt calibration with intelligent validation.
"""

from __future__ import annotations

import enum
import math
import statistics
import time
from dataclasses import dataclass
from typing import Callable, List, Optional, Sequence

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
    """Snapshot data for current calibration step progress and feedback overlay."""
    step: CalibrationStep
    step_number: int
    total_steps: int
    instruction: str
    displayed_instruction: str
    camera_mode: str
    countdown_seconds: int
    live_angle: float
    captured_value: Optional[float]
    completion_ratio: float
    target_direction: str
    detected_direction: str
    status_message: str
    total_steering_range: Optional[float] = None
    error_message: Optional[str] = None


class CalibrationSession:
    """
    Step-by-step state machine for capturing user steering angles with movement validation.

    Parameters
    ----------
    config: Optional[CalibrationConfig]
        Calibration configuration settings.
    """

    def __init__(self, config: Optional[CalibrationConfig] = None) -> None:
        self.config = config or CalibrationConfig()

        self._step = CalibrationStep.NOT_STARTED
        self._phase: str = "MONITORING"  # "MONITORING", "SUCCESS_PAUSE"
        self._step_start_time: float = 0.0
        self._phase_start_time: float = 0.0
        self._samples: List[float] = []

        self._center_angle: Optional[float] = None
        self._left_limit: Optional[float] = None
        self._right_limit: Optional[float] = None

        self._error_message: Optional[str] = None
        self._status_message: str = "Ready to calibrate."
        self._last_live_angle: float = 0.0
        self._stable_hold_time: float = 0.0
        self._last_stable_angle: float = 0.0

        # Sound / Event hooks
        self.on_step_started: Optional[Callable[[CalibrationStep], None]] = None
        self.on_step_captured: Optional[Callable[[CalibrationStep, float], None]] = None
        self.on_calibration_completed: Optional[Callable[[CalibrationData], None]] = None
        self.on_calibration_saved: Optional[Callable[[CalibrationData], None]] = None
        self.on_calibration_cancelled: Optional[Callable[[], None]] = None
        self.on_calibration_failed: Optional[Callable[[str], None]] = None

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
        """User accepts the captured calibration summary on Review Screen."""
        if self._step == CalibrationStep.SUMMARY and self.result_data is not None:
            self._step = CalibrationStep.COMPLETE
            self._error_message = None
            self._status_message = "✓ Calibration Saved"
            if self.on_calibration_saved:
                self.on_calibration_saved(self.result_data)
            return True
        return False

    def process_frame(
        self, hand_analyses: Optional[Sequence[HandAnalysis]], dt: float = 0.033
    ) -> StepSnapshot:
        """
        Process a single video frame during calibration with movement direction validation.
        """
        if self._step in (CalibrationStep.NOT_STARTED, CalibrationStep.COMPLETE, CalibrationStep.SUMMARY, CalibrationStep.FAILED):
            return self._build_snapshot()

        # Check hand availability & error handling
        if not hand_analyses or len(hand_analyses) == 0:
            self._error_message = "Hand Lost"
            self._status_message = "Hand Lost - Please return your hand to the camera."
            return self._build_snapshot()

        if len(hand_analyses) > 1:
            self._error_message = "Multiple hands detected"
            self._status_message = "Multiple hands detected - Please show only one hand."
            return self._build_snapshot()

        self._error_message = None

        # Extract hand tilt angle
        angle_deg = self._extract_angle(hand_analyses[0])
        self._last_live_angle = angle_deg
        now = time.monotonic()

        # Handle Transition Delay Phase (TRANSITION_PAUSE & TRANSITION_COUNTDOWN)
        if self._phase in ("TRANSITION_PAUSE", "TRANSITION_COUNTDOWN"):
            elapsed_trans = now - self._phase_start_time
            pause_dur = self.config.transition_pause_duration
            cd_dur = self.config.transition_countdown_duration

            if self._phase == "TRANSITION_PAUSE":
                if elapsed_trans >= pause_dur:
                    if cd_dur > 0.0:
                        self._phase = "TRANSITION_COUNTDOWN"
                    else:
                        self._finish_transition()
                else:
                    self._update_transition_status(pause_phase=True, countdown=0)
                    return self._build_snapshot()

            if self._phase == "TRANSITION_COUNTDOWN":
                cd_elapsed = elapsed_trans if pause_dur <= 0.0 else (elapsed_trans - pause_dur)
                if cd_elapsed >= cd_dur:
                    self._finish_transition()
                else:
                    rem_cd = max(1, int(math.ceil(cd_dur - cd_elapsed)))
                    self._update_transition_status(pause_phase=False, countdown=rem_cd)
                    return self._build_snapshot()

        self._samples.append(angle_deg)

        # Step 1: CENTER
        if self._step == CalibrationStep.CENTER:
            if self._phase == "MONITORING":
                # Allow user's natural comfortable straight-ahead posture (within ±30° initial bounds)
                if abs(angle_deg) > 30.0:
                    self._stable_hold_time = 0.0
                    self._status_message = "Hold your hand straight ahead in natural center position."
                else:
                    if abs(angle_deg - self._last_stable_angle) < 3.0:
                        self._stable_hold_time += dt
                    else:
                        self._stable_hold_time = 0.0
                    self._last_stable_angle = angle_deg
                    self._status_message = f"Holding natural center... ({self._stable_hold_time:.1f}s)"

                    if self._stable_hold_time >= self.config.stable_hold_duration or len(self._samples) >= self.config.required_frames_per_step * 2:
                        self._center_angle = round(statistics.median(self._samples), 2)
                        self._phase = "SUCCESS_PAUSE"
                        self._phase_start_time = now
                        self._status_message = "✓ Center Captured"
                        if self.on_step_captured:
                            self.on_step_captured(CalibrationStep.CENTER, self._center_angle)
            if self._phase == "SUCCESS_PAUSE":
                if (now - self._phase_start_time) >= self.config.success_message_duration or self.config.success_message_duration <= 0.0:
                    self._transition_to(CalibrationStep.LEFT)

        # Step 2: LEFT
        elif self._step == CalibrationStep.LEFT:
            if self._phase == "MONITORING":
                delta = angle_deg - (self._center_angle or 0.0)
                if delta > 5.0:
                    self._stable_hold_time = 0.0
                    self._status_message = "Wrong direction detected. Rotate LEFT."
                elif delta > -self.config.min_movement_threshold:
                    self._stable_hold_time = 0.0
                    self._status_message = "Rotate further LEFT."
                else:
                    # Valid left rotation detected
                    if abs(angle_deg - self._last_stable_angle) < 3.0:
                        self._stable_hold_time += dt
                    else:
                        self._stable_hold_time = 0.0
                    self._last_stable_angle = angle_deg
                    self._status_message = f"Holding stable... ({self._stable_hold_time:.1f}s)"

                    if self._stable_hold_time >= self.config.stable_hold_duration or len(self._samples) >= self.config.required_frames_per_step * 2:
                        self._left_limit = round(statistics.median([s for s in self._samples if s - (self._center_angle or 0.0) <= -self.config.min_movement_threshold] or self._samples), 2)
                        self._phase = "SUCCESS_PAUSE"
                        self._phase_start_time = now
                        self._status_message = "✓ Left Captured"
                        if self.on_step_captured:
                            self.on_step_captured(CalibrationStep.LEFT, self._left_limit)

            if self._phase == "SUCCESS_PAUSE":
                if (now - self._phase_start_time) >= self.config.success_message_duration or self.config.success_message_duration <= 0.0:
                    self._transition_to(CalibrationStep.RIGHT)

        # Step 3: RIGHT
        elif self._step == CalibrationStep.RIGHT:
            if self._phase == "MONITORING":
                delta = angle_deg - (self._center_angle or 0.0)
                if delta < -5.0:
                    self._stable_hold_time = 0.0
                    self._status_message = "Wrong direction detected. Rotate RIGHT."
                elif delta < self.config.min_movement_threshold:
                    self._stable_hold_time = 0.0
                    self._status_message = "Rotate further RIGHT."
                else:
                    # Valid right rotation detected
                    if abs(angle_deg - self._last_stable_angle) < 3.0:
                        self._stable_hold_time += dt
                    else:
                        self._stable_hold_time = 0.0
                    self._last_stable_angle = angle_deg
                    self._status_message = f"Holding stable... ({self._stable_hold_time:.1f}s)"

                    if self._stable_hold_time >= self.config.stable_hold_duration or len(self._samples) >= self.config.required_frames_per_step * 2:
                        self._right_limit = round(statistics.median([s for s in self._samples if s - (self._center_angle or 0.0) >= self.config.min_movement_threshold] or self._samples), 2)

                        # Range validation: left < center < right
                        if (
                            self._center_angle is not None
                            and self._left_limit is not None
                            and self._right_limit is not None
                            and (self._left_limit < self._center_angle < self._right_limit)
                            and abs(self._center_angle - self._left_limit) >= self.config.min_steering_range
                            and abs(self._right_limit - self._center_angle) >= self.config.min_steering_range
                        ):
                            self._phase = "SUCCESS_PAUSE"
                            self._phase_start_time = now
                            self._status_message = "✓ Right Captured"
                            if self.on_step_captured:
                                self.on_step_captured(CalibrationStep.RIGHT, self._right_limit)
                        else:
                            self._step = CalibrationStep.FAILED
                            self._error_message = "Calibration Failed - Please recalibrate."
                            self._status_message = "Calibration Failed - Please recalibrate."
                            if self.on_calibration_failed:
                                self.on_calibration_failed("Calibration Failed - Invalid range.")

            if self._phase == "SUCCESS_PAUSE":
                if (now - self._phase_start_time) >= self.config.success_message_duration or self.config.success_message_duration <= 0.0:
                    self._transition_to(CalibrationStep.SUMMARY)

        return self._build_snapshot()

    def _finish_transition(self) -> None:
        now = time.monotonic()
        if self._step == CalibrationStep.SUMMARY:
            self._phase = "REVIEW"
            self._status_message = "Review Calibration - [S] Save | [R] Recalibrate | [ESC] Cancel"
            if self.on_calibration_completed and self.result_data is not None:
                self.on_calibration_completed(self.result_data)
        else:
            self._phase = "MONITORING"
            self._step_start_time = now
            self._samples.clear()
            self._stable_hold_time = 0.0
            self._last_stable_angle = self._last_live_angle
            self._update_step_status_message()

    def _update_transition_status(self, pause_phase: bool, countdown: int) -> None:
        mirrored = self.config.camera_mirrored
        if self._step == CalibrationStep.LEFT:
            next_target = "Rotate RIGHT" if mirrored else "Rotate LEFT"
            if pause_phase:
                self._status_message = f"Prepare for the next step... Next: {next_target}"
            else:
                self._status_message = f"Starting in {countdown}..."
        elif self._step == CalibrationStep.RIGHT:
            next_target = "Rotate LEFT" if mirrored else "Rotate RIGHT"
            if pause_phase:
                self._status_message = f"Prepare for the next step... Next: {next_target}"
            else:
                self._status_message = f"Starting in {countdown}..."
        elif self._step == CalibrationStep.SUMMARY:
            if pause_phase:
                self._status_message = "Prepare for review screen..."
            else:
                self._status_message = f"Opening review screen in {countdown}..."

    def _update_step_status_message(self) -> None:
        if self._step == CalibrationStep.CENTER:
            self._status_message = "Hold your hand naturally in the center."
        elif self._step == CalibrationStep.LEFT:
            self._status_message = "Rotate your hand fully RIGHT." if self.config.camera_mirrored else "Rotate your hand fully LEFT."
        elif self._step == CalibrationStep.RIGHT:
            self._status_message = "Rotate your hand fully LEFT." if self.config.camera_mirrored else "Rotate your hand fully RIGHT."
        elif self._step == CalibrationStep.SUMMARY:
            self._status_message = "Review Calibration - [S] Save | [R] Recalibrate | [ESC] Cancel"

    def _extract_angle(self, analysis: HandAnalysis) -> float:
        """Extract hand tilt angle in degrees from hand landmarks."""
        state = getattr(analysis, "hand_state", None)
        if not state or not hasattr(state, "landmarks") or not state.landmarks or len(state.landmarks) < 21:
            return 0.0

        lms = state.landmarks
        wrist = lms[0]
        middle_mcp = lms[9]

        # Physical user coordinate system (Physical LEFT -> negative angle, Physical RIGHT -> positive angle)
        # In raw camera frame facing user: User LEFT -> camera right (middle_mcp.x > wrist.x), User RIGHT -> camera left (middle_mcp.x < wrist.x)
        dx = wrist.x - middle_mcp.x
        dy = middle_mcp.y - wrist.y

        # In image space, y points down. Vector pointing up is (dx, -dy).
        angle_rad = math.atan2(dx, -dy)
        return math.degrees(angle_rad)

    def _transition_to(self, step: CalibrationStep) -> None:
        self._step = step
        self._step_start_time = time.monotonic()
        self._phase_start_time = time.monotonic()
        self._samples.clear()
        self._error_message = None
        self._stable_hold_time = 0.0
        self._last_stable_angle = self._last_live_angle

        if step in (CalibrationStep.LEFT, CalibrationStep.RIGHT, CalibrationStep.SUMMARY):
            if self.config.transition_pause_duration > 0.0:
                self._phase = "TRANSITION_PAUSE"
            elif self.config.transition_countdown_duration > 0.0:
                self._phase = "TRANSITION_COUNTDOWN"
            else:
                self._finish_transition()
        else:
            self._phase = "MONITORING"
            self._update_step_status_message()

        if self.on_step_started and step not in (CalibrationStep.SUMMARY, CalibrationStep.COMPLETE, CalibrationStep.FAILED):
            self.on_step_started(step)

    def _build_snapshot(self) -> StepSnapshot:
        elapsed = time.monotonic() - self._step_start_time if self._step_start_time > 0 else 0.0

        # Countdown seconds calculation
        if self._phase == "TRANSITION_COUNTDOWN":
            trans_cd_elapsed = (time.monotonic() - self._phase_start_time) if self.config.transition_pause_duration <= 0.0 else (time.monotonic() - self._phase_start_time - self.config.transition_pause_duration)
            countdown = max(1, int(math.ceil(self.config.transition_countdown_duration - trans_cd_elapsed)))
        elif self._phase == "TRANSITION_PAUSE":
            countdown = int(math.ceil(self.config.transition_countdown_duration)) if self.config.transition_countdown_duration > 0.0 else 0
        elif self._step == CalibrationStep.CENTER and self._phase == "MONITORING":
            countdown = max(0, int(math.ceil(self.config.countdown_duration - elapsed)))
        else:
            countdown = 0

        step_num = 1
        target_dir = "CENTER"
        instruction = ""
        captured_val = None
        ratio = 0.0

        delta = self._last_live_angle - (self._center_angle or 0.0)
        if delta <= -5.0:
            detected_dir = "LEFT"
        elif delta >= 5.0:
            detected_dir = "RIGHT"
        else:
            detected_dir = "CENTER"

        if self._step == CalibrationStep.CENTER:
            step_num = 1
            target_dir = "CENTER"
            instruction = "Hold your hand naturally in the center."
            captured_val = self._center_angle
            ratio = min(1.0, elapsed / max(0.01, self.config.countdown_duration))
        elif self._step == CalibrationStep.LEFT:
            step_num = 2
            target_dir = "LEFT"
            instruction = "Rotate your hand fully LEFT."
            captured_val = self._left_limit
            ratio = min(1.0, self._stable_hold_time / max(0.01, self.config.stable_hold_duration))
        elif self._step == CalibrationStep.RIGHT:
            step_num = 3
            target_dir = "RIGHT"
            instruction = "Rotate your hand fully RIGHT."
            captured_val = self._right_limit
            ratio = min(1.0, self._stable_hold_time / max(0.01, self.config.stable_hold_duration))
        elif self._step == CalibrationStep.SUMMARY:
            step_num = 4
            target_dir = "REVIEW"
            instruction = "Review Calibration Summary"
            ratio = 1.0
        elif self._step == CalibrationStep.COMPLETE:
            step_num = 4
            target_dir = "COMPLETE"
            instruction = "✓ Calibration Complete & Saved"
            ratio = 1.0
        elif self._step == CalibrationStep.FAILED:
            step_num = 0
            target_dir = "FAILED"
            instruction = "Calibration Failed. Please recalibrate."
            ratio = 0.0

        # Instruction for transition phase and monitoring step
        if self._phase == "TRANSITION_PAUSE":
            if self._step == CalibrationStep.LEFT:
                disp_instruction = "Next: Rotate LEFT"
            elif self._step == CalibrationStep.RIGHT:
                disp_instruction = "Next: Rotate RIGHT"
            elif self._step == CalibrationStep.SUMMARY:
                disp_instruction = "Preparing Calibration Summary..."
            else:
                disp_instruction = instruction
        elif self._phase == "TRANSITION_COUNTDOWN":
            if self._step == CalibrationStep.LEFT:
                disp_instruction = f"Rotate your hand fully LEFT (Starting in {countdown}...)"
            elif self._step == CalibrationStep.RIGHT:
                disp_instruction = f"Rotate your hand fully RIGHT (Starting in {countdown}...)"
            elif self._step == CalibrationStep.SUMMARY:
                disp_instruction = f"Preparing Calibration Summary ({countdown}...)"
            else:
                disp_instruction = instruction
        else:
            if self._step == CalibrationStep.LEFT:
                disp_instruction = "Rotate your hand fully LEFT."
            elif self._step == CalibrationStep.RIGHT:
                disp_instruction = "Rotate your hand fully RIGHT."
            else:
                disp_instruction = instruction

        if self._phase in ("TRANSITION_PAUSE", "TRANSITION_COUNTDOWN"):
            total_dur = self.config.transition_pause_duration + self.config.transition_countdown_duration
            ratio = min(1.0, (time.monotonic() - self._phase_start_time) / max(0.01, total_dur))

        camera_mode_str = "Mirrored" if self.config.camera_mirrored else "Normal"

        total_range = None
        if self._left_limit is not None and self._right_limit is not None:
            total_range = round(abs(self._right_limit - self._left_limit), 2)

        return StepSnapshot(
            step=self._step,
            step_number=step_num,
            total_steps=3,
            instruction=instruction,
            displayed_instruction=disp_instruction,
            camera_mode=camera_mode_str,
            countdown_seconds=countdown,
            live_angle=round(self._last_live_angle, 2),
            captured_value=captured_val,
            completion_ratio=ratio,
            target_direction=target_dir,
            detected_direction=detected_dir,
            status_message=self._status_message,
            total_steering_range=total_range,
            error_message=self._error_message,
        )

