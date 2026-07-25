"""
gesturedrive.gui.worker
=======================
PipelineWorker: Qt worker thread driving the end-to-end real-time control pipeline without blocking the main UI thread.
"""

from __future__ import annotations

import logging
import time
from collections import deque
from typing import Deque

import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal

from actions import ActionEngine, ActionState
from calibration.calibration_manager import CalibrationManager
from calibration.calibration_overlay import render_calibration_overlay
from calibration.calibration_session import CalibrationStep
from camera.camera import OpenCVCameraSource
from config.schema import CameraConfig, TrackingConfig
from controller import IVirtualController, NullController, XboxController, XboxOutputPlugin
from core.exceptions import ControllerError
from analysis import HandAnalysis, HandAnalyzer
from gestures.builtins import (
    FistGesture,
    OpenPalmGesture,
    PeaceGesture,
    PinchGesture,
    PointGesture,
    ThumbsUpGesture,
)
from gestures.manager import GestureManager
from gestures.registry import GestureRegistry
from tracking.hand_tracker import MediaPipeHandTracker, TrackingResult

logger = logging.getLogger(__name__)


class _RollingFPS:
    """Rolling window FPS calculation."""

    def __init__(self, window: int = 60) -> None:
        self._ts: Deque[float] = deque(maxlen=window)

    def tick(self) -> None:
        self._ts.append(time.monotonic())

    @property
    def fps(self) -> float:
        if len(self._ts) < 2:
            return 0.0
        elapsed = self._ts[-1] - self._ts[0]
        return 0.0 if elapsed <= 0.0 else (len(self._ts) - 1) / elapsed


class PipelineWorker(QThread):
    """
    Worker thread that runs the real-time processing loop.

    Signals
    -------
    frame_processed: (np.ndarray, float, dict)
        Emitted for each frame with the annotated image array, live FPS, and telemetry data dict.
    status_changed: (str, str, str)
        Emitted when a component status updates: (component_name, status_str, state_level).
    error_occurred: (str, str)
        Emitted when an error occurs: (title, message).
    """

    frame_processed = Signal(object, float, dict)
    status_changed = Signal(str, str, str)
    error_occurred = Signal(str, str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._running: bool = False

        # Backend handles
        self.camera: OpenCVCameraSource | None = None
        self.tracker: MediaPipeHandTracker | None = None
        self.hand_analyzer: HandAnalyzer | None = None
        self.gesture_manager: GestureManager | None = None
        self.action_engine: ActionEngine | None = None
        self.xbox_controller: IVirtualController | None = None
        self.xbox_plugin: XboxOutputPlugin | None = None
        self.calibration_manager: CalibrationManager | None = None
        self.fps_counter = _RollingFPS(window=60)

    def stop(self) -> None:
        """Signal loop to terminate."""
        self._running = False

    def apply_live_config(self, camera_config=None, gesture_config=None) -> None:
        """Apply camera and steering pipeline settings live defensively without crashing."""
        if gesture_config and self.action_engine:
            pipe = getattr(self.action_engine, "steering_pipeline", None)
            if pipe:
                try:
                    if hasattr(gesture_config, "max_steering_angle") and hasattr(pipe, "max_steering_angle"):
                        pipe.max_steering_angle = float(gesture_config.max_steering_angle)
                        logger.info("PipelineWorker: Live max_steering_angle updated to %.1f°.", pipe.max_steering_angle)

                    if hasattr(gesture_config, "steering_deadzone") and hasattr(pipe, "steering_deadzone"):
                        pipe.steering_deadzone = float(gesture_config.steering_deadzone)
                        logger.info("PipelineWorker: Live steering_deadzone updated to %.2f.", pipe.steering_deadzone)

                    if hasattr(gesture_config, "steering_sensitivity") and hasattr(pipe, "steering_sensitivity"):
                        pipe.steering_sensitivity = float(gesture_config.steering_sensitivity)
                        logger.info("PipelineWorker: Live steering_sensitivity updated to %.2f.", pipe.steering_sensitivity)

                    if hasattr(gesture_config, "steering_smoothing_alpha") and hasattr(pipe, "steering_ema_alpha"):
                        pipe.steering_ema_alpha = float(gesture_config.steering_smoothing_alpha)
                        logger.info("PipelineWorker: Live steering_ema_alpha updated to %.2f.", pipe.steering_ema_alpha)

                    logger.info("PipelineWorker: Live steering pipeline configuration applied successfully.")
                except Exception as exc:
                    logger.warning("PipelineWorker: Live steering configuration update skipped safely: %s", exc)

    def run(self) -> None:
        """Execute processing loop on background thread."""
        self._running = True

        # 1. Instantiate backend pipeline services
        try:
            cam_cfg = CameraConfig()
            self.camera = OpenCVCameraSource(
                device_index=cam_cfg.device_index,
                target_width=cam_cfg.width,
                target_height=cam_cfg.height,
                target_fps=cam_cfg.fps,
            )

            trk_cfg = TrackingConfig()
            self.tracker = MediaPipeHandTracker(
                max_num_hands=trk_cfg.max_num_hands,
                min_detection_confidence=trk_cfg.min_detection_confidence,
                min_tracking_confidence=trk_cfg.min_tracking_confidence,
                model_complexity=trk_cfg.model_complexity,
            )

            self.hand_analyzer = HandAnalyzer()

            # Gesture Manager
            registry = GestureRegistry()
            registry.register(OpenPalmGesture())
            registry.register(PointGesture())
            registry.register(PeaceGesture())
            registry.register(FistGesture())
            registry.register(ThumbsUpGesture())
            registry.register(PinchGesture())
            self.gesture_manager = GestureManager(registry=registry)

            # Action Engine & Calibration Manager
            self.action_engine = ActionEngine()
            self.calibration_manager = CalibrationManager()
            self.calibration_manager.bind_steering_pipeline(self.action_engine)

            # Virtual Xbox Controller
            try:
                self.xbox_controller = XboxController()
                self.xbox_controller.connect()
                self.status_changed.emit("Controller", "Connected", "good")
            except ControllerError as exc:
                logger.warning("XboxController fallback to NullController: %s", exc)
                self.xbox_controller = NullController()
                self.xbox_controller.connect()
                self.status_changed.emit("Controller", "Safe Mode", "warn")

            self.xbox_plugin = XboxOutputPlugin(controller=self.xbox_controller)

        except Exception as exc:
            logger.error("Backend instantiation failed: %s", exc, exc_info=True)
            self.error_occurred.emit("Backend Error", f"Failed to initialize backend components: {exc}")
            self._running = False
            return

        # 2. Open camera
        try:
            self.camera.open()
            self.status_changed.emit("Camera", "Connected", "good")
        except Exception as exc:
            logger.error("Camera open failed: %s", exc)
            self.status_changed.emit("Camera", "Failed", "bad")
            self.error_occurred.emit("Camera Error", f"Could not open camera device: {exc}")
            self._running = False
            return

        # 3. Initialise MediaPipe Hand Tracker
        try:
            self.tracker.initialise()
            self.status_changed.emit("MediaPipe", "Running", "good")
        except Exception as exc:
            logger.error("Tracker init failed: %s", exc)
            self.status_changed.emit("MediaPipe", "Failed", "bad")
            self.error_occurred.emit("Tracking Error", f"Could not initialize MediaPipe tracker: {exc}")
            self.camera.release()
            self._running = False
            return

        # Status update for calibration
        cal_active = self.calibration_manager.active_calibration is not None
        cal_str = "Loaded" if cal_active else "Default"
        cal_state = "good" if cal_active else "warn"
        self.status_changed.emit("Calibration", cal_str, cal_state)

        # 4. Processing Loop
        try:
            while self._running:
                loop_start_time = time.monotonic()
                try:
                    frame = self.camera.read()
                except Exception as exc:
                    logger.error("Frame capture error: %s", exc)
                    self.error_occurred.emit("Capture Error", f"Camera read error: {exc}")
                    break

                try:
                    result = self.tracker.process_frame(frame)
                except Exception as exc:
                    logger.warning("Tracking frame error: %s", exc)
                    continue

                self.fps_counter.tick()

                # Process analyses & pipeline
                analyses: list[HandAnalysis] = []
                gesture_name = "None"
                gesture_confidence = 0.0
                action_name = "Idle"
                steering_angle = 0.0
                norm_steering = 0.0
                raw_angle = 0.0
                tracking_conf = 0.0
                direction = "CENTER"

                if result.hands:
                    analyses = self.hand_analyzer.analyze_hands(result.hands)
                    gesture_results = self.gesture_manager.process_hands(analyses)
                    action_state = self.action_engine.process(gesture_results, analyses)
                    self.xbox_plugin.process(action_state)

                    norm_steering = getattr(action_state, "steering", 0.0)
                    raw_sensor = getattr(action_state, "raw_sensor_angle", 0.0)
                    adjusted_angle = getattr(action_state, "adjusted_steering_angle", norm_steering * 30.0)
                    steering_angle = adjusted_angle
                    raw_angle = raw_sensor

                    # Configurable Neutral Deadzone (e.g. |norm_steering| <= 0.03 or |adjusted_angle| <= 1.0°)
                    if abs(norm_steering) <= 0.03 or abs(adjusted_angle) <= 1.0:
                        direction = "CENTER"
                    elif norm_steering < -0.03:
                        direction = "LEFT"
                    else:
                        direction = "RIGHT"

                    if gesture_results and getattr(gesture_results[0], "detected", False):
                        gesture_name = getattr(gesture_results[0], "gesture_name", "None")
                        gesture_confidence = getattr(gesture_results[0], "confidence", 0.0)

                    if getattr(action_state, "accelerator", False):
                        action_name = "Accelerator"
                    elif getattr(action_state, "brake", False):
                        action_name = "Brake"
                    elif getattr(action_state, "handbrake", False):
                        action_name = "Handbrake"
                    elif abs(norm_steering) > 0.02:
                        action_name = "Steering"

                    hand0 = result.hands[0]
                    tracking_conf = float(getattr(hand0, "score", getattr(hand0, "confidence", 0.95)))
                else:
                    action_state = self.action_engine.process([], [])
                    self.xbox_plugin.process(action_state)

                # Calibration session snapshot if active
                cal_snap = None
                if self.calibration_manager and self.calibration_manager.is_session_active:
                    cal_snap = self.calibration_manager.session.process_frame(analyses)

                # Controller hardware output state
                ctrl_is_xbox = isinstance(self.xbox_controller, XboxController)
                ctrl_status_str = "Connected (ViGEmBus)" if ctrl_is_xbox else "Safe Mode (Null)"
                stick_x = int(norm_steering * 32767)
                rt_val = 255 if action_name == "Accelerator" else 0
                lt_val = 255 if action_name == "Brake" else 0
                buttons_pressed = "Button A" if action_name == "Handbrake" else "None"

                elapsed_ms = (time.monotonic() - loop_start_time) * 1000.0

                telemetry = {
                    "steering_angle": steering_angle,
                    "raw_steering": raw_angle,
                    "normalized_steering": norm_steering,
                    "direction": direction,
                    "gesture": gesture_name,
                    "gesture_confidence": gesture_confidence,
                    "action": action_name,
                    "camera_fps": self.fps_counter.fps,
                    "processing_fps": self.fps_counter.fps,
                    "latency_ms": elapsed_ms,
                    "tracking_confidence": tracking_conf,
                    "controller_status": ctrl_status_str,
                    "left_stick_x": stick_x,
                    "accelerator_rt": rt_val,
                    "brake_lt": lt_val,
                    "buttons_pressed": buttons_pressed,
                    "camera_name": "Integrated Webcam",
                    "profile_name": "Default",
                    "calibration_snapshot": cal_snap,
                }

                self.frame_processed.emit(result.annotated_image, self.fps_counter.fps, telemetry)

        finally:
            self._cleanup_resources()

    def _cleanup_resources(self) -> None:
        """Release camera, tracker, and controller resources cleanly."""
        if self.tracker:
            try:
                self.tracker.shutdown()
            except Exception as exc:
                logger.warning("Error shutting down tracker: %s", exc)

        if self.camera:
            try:
                self.camera.release()
            except Exception as exc:
                logger.warning("Error releasing camera: %s", exc)

        if self.xbox_controller:
            try:
                self.xbox_controller.disconnect()
            except Exception as exc:
                logger.warning("Error disconnecting controller: %s", exc)

        self.status_changed.emit("Camera", "Stopped", "neutral")
        self.status_changed.emit("MediaPipe", "Idle", "neutral")
        self.status_changed.emit("Controller", "Disconnected", "neutral")
        logger.info("PipelineWorker resources released cleanly.")
