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
from actions.config import ActionEngineConfig
from calibration.calibration_manager import CalibrationManager
from calibration.calibration_overlay import render_calibration_overlay
from calibration.calibration_session import CalibrationStep
from camera.camera import OpenCVCameraSource
from camera.frame_buffer import AsyncCameraCapture, LatestFrameBuffer
from config.schema import CameraConfig, ControllerConfig, GestureConfig, TrackingConfig
from controller import IVirtualController, NullController, XboxController, XboxOutputPlugin
from core.exceptions import ControllerError
from desktop import AppMode, DesktopController, ModeManager
from analysis import HandAnalysis, HandAnalyzer
from gestures.builtins import (
    FistGesture,
    OpenPalmGesture,
    PeaceGesture,
    PinchGesture,
    PinchPinkyGesture,
    PointGesture,
    ThumbsDownGesture,
    ThumbsUpGesture,
)
from gestures.manager import GestureManager
from gestures.registry import GestureRegistry
from tracking.hand_selection import select_primary_hand_index
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
        self.async_capture: AsyncCameraCapture | None = None
        self.tracker: MediaPipeHandTracker | None = None
        self.hand_analyzer: HandAnalyzer | None = None
        self.gesture_manager: GestureManager | None = None
        self.action_engine: ActionEngine | None = None
        self.xbox_controller: IVirtualController | None = None
        self.xbox_plugin: XboxOutputPlugin | None = None
        self.calibration_manager: CalibrationManager | None = None
        self.desktop_controller: DesktopController | None = None
        self.mode_manager: ModeManager | None = None
        self.profile_name: str = "Default"
        self.profile_camera_config: CameraConfig = CameraConfig()
        self.profile_tracking_config: TrackingConfig = TrackingConfig()
        self.profile_gesture_config: GestureConfig = GestureConfig()
        self.profile_controller_config: ControllerConfig = ControllerConfig()
        self.profile_desktop_config: dict = {}
        self.fps_counter = _RollingFPS(window=60)

    def stop(self) -> None:
        """Signal loop to terminate."""
        self._running = False

    def configure_from_profile(self, profile) -> None:
        """Cache profile-backed settings before the worker thread starts."""
        self.profile_name = getattr(profile, "name", self.profile_name)

        camera_cfg = getattr(profile, "camera", None)
        if isinstance(camera_cfg, dict):
            self.profile_camera_config = CameraConfig.from_dict(camera_cfg)

        steering_cfg = getattr(profile, "steering", None)
        if isinstance(steering_cfg, dict):
            self.profile_gesture_config = GestureConfig.from_dict(steering_cfg)

        controller_cfg = getattr(profile, "controller", None)
        if isinstance(controller_cfg, dict):
            self.profile_controller_config = ControllerConfig.from_dict(controller_cfg)

        desktop_cfg = getattr(profile, "desktop", None)
        if isinstance(desktop_cfg, dict):
            self.profile_desktop_config = dict(desktop_cfg)

        tracking_cfg = getattr(profile, "tracking", None)
        if isinstance(tracking_cfg, dict):
            self.profile_tracking_config = TrackingConfig.from_dict(tracking_cfg)

    def apply_profile(self, profile) -> None:
        """Apply a profile to the live worker, updating what can change immediately."""
        self.configure_from_profile(profile)
        if self.mode_manager and self.profile_desktop_config:
            self.mode_manager.set_mode(self.profile_desktop_config.get("mode", "driving"))
        self.apply_live_config(self.profile_camera_config, self.profile_gesture_config)
        self.apply_controller_config(self.profile_controller_config)
        if self.desktop_controller and self.profile_desktop_config:
            self.desktop_controller.apply_config(self.profile_desktop_config)

    def apply_controller_config(self, controller_config: ControllerConfig | dict | None) -> None:
        """Update the active virtual controller backend."""
        if controller_config is None:
            return

        if isinstance(controller_config, dict):
            controller_config = ControllerConfig.from_dict(controller_config)

        self.profile_controller_config = controller_config

        if self.xbox_plugin is None and self.xbox_controller is None:
            return

        try:
            if self.xbox_controller is not None:
                try:
                    self.xbox_controller.disconnect()
                except Exception:
                    pass

            emu = str(controller_config.emulation_type).lower()
            if emu == "null":
                self.xbox_controller = NullController()
            else:
                self.xbox_controller = XboxController(config=controller_config)

            self.xbox_controller.connect()
            self.xbox_plugin = XboxOutputPlugin(controller=self.xbox_controller)
            logger.info("PipelineWorker: controller backend reconfigured to %s.", emu)
        except Exception as exc:
            logger.warning("PipelineWorker: controller reconfiguration failed: %s", exc)

    def apply_live_config(self, camera_config=None, gesture_config=None) -> None:
        """Apply camera and steering pipeline settings live defensively without crashing."""
        if camera_config is not None:
            self.profile_camera_config = camera_config if isinstance(camera_config, CameraConfig) else CameraConfig.from_dict(
                camera_config.to_dict() if hasattr(camera_config, "to_dict") else dict(camera_config)
            )

        if gesture_config and self.action_engine:
            self.profile_gesture_config = gesture_config if isinstance(gesture_config, GestureConfig) else GestureConfig.from_dict(
                gesture_config.to_dict() if hasattr(gesture_config, "to_dict") else dict(gesture_config)
            )
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

                    if hasattr(gesture_config, "steering_inversion") and hasattr(pipe, "steering_inversion"):
                        pipe.steering_inversion = bool(gesture_config.steering_inversion)
                        logger.info("PipelineWorker: Live steering_inversion updated to %s.", pipe.steering_inversion)

                    if hasattr(gesture_config, "steering_curve_exponent") and hasattr(pipe, "steering_curve_exponent"):
                        pipe.steering_curve_exponent = float(gesture_config.steering_curve_exponent)

                    if hasattr(gesture_config, "steering_auto_center_rate") and hasattr(pipe, "steering_auto_center_rate"):
                        pipe.steering_auto_center_rate = float(gesture_config.steering_auto_center_rate)

                    logger.info("PipelineWorker: Live steering pipeline configuration applied successfully.")
                except Exception as exc:
                    logger.warning("PipelineWorker: Live steering configuration update skipped safely: %s", exc)

    def run(self) -> None:
        """Execute processing loop on background thread."""
        self._running = True

        # 1. Instantiate backend pipeline services
        try:
            cam_cfg = self.profile_camera_config
            self.camera = OpenCVCameraSource.from_config(cam_cfg)

            trk_cfg = self.profile_tracking_config
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
            registry.register(ThumbsDownGesture())
            registry.register(PinchGesture())
            registry.register(PinchPinkyGesture())
            self.gesture_manager = GestureManager(registry=registry)

            # Action Engine & Calibration Manager
            gesture_cfg = self.profile_gesture_config
            self.action_engine = ActionEngine(
                config=ActionEngineConfig(
                    max_steering_angle=gesture_cfg.max_steering_angle,
                    steering_deadzone=gesture_cfg.steering_deadzone,
                    steering_sensitivity=gesture_cfg.steering_sensitivity,
                    steering_curve_exponent=gesture_cfg.steering_curve_exponent,
                    steering_ema_alpha=gesture_cfg.steering_smoothing_alpha,
                    steering_auto_center_rate=gesture_cfg.steering_auto_center_rate,
                    steering_inversion=gesture_cfg.steering_inversion,
                )
            )
            self.calibration_manager = CalibrationManager()
            self.calibration_manager.bind_steering_pipeline(self.action_engine)

            # Desktop Controller & Mode Manager
            self.desktop_controller = DesktopController()
            if self.profile_desktop_config:
                self.desktop_controller.apply_config(self.profile_desktop_config)
            if self.mode_manager is None:
                self.mode_manager = ModeManager()

            # Virtual Xbox Controller
            try:
                if str(self.profile_controller_config.emulation_type).lower() == "null":
                    self.xbox_controller = NullController()
                else:
                    self.xbox_controller = XboxController(config=self.profile_controller_config)
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

        # 2. Open camera & start decoupled background capture (Thread A)
        try:
            self.camera.open()
            self.async_capture = AsyncCameraCapture(camera=self.camera)
            self.async_capture.start()
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
            if self.async_capture:
                self.async_capture.stop()
            self.camera.release()
            self._running = False
            return

        # Status update for calibration
        cal_active = self.calibration_manager.active_calibration is not None
        cal_str = "Loaded" if cal_active else "Default"
        cal_state = "good" if cal_active else "warn"
        self.status_changed.emit("Calibration", cal_str, cal_state)

        # 4. Processing Loop (Thread B: Consumes newest available frame)
        try:
            while self._running:
                # Wait for newest frame from buffer (latest-frame-wins; zero stale accumulation)
                frame = self.async_capture.get_latest_frame(timeout=0.05) if self.async_capture else None
                if frame is None:
                    continue

                proc_start_time = time.monotonic()
                cap_timestamp = getattr(frame, "capture_timestamp", proc_start_time)
                cap_to_proc_latency_ms = max(0.0, (proc_start_time - cap_timestamp) * 1000.0)

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

                desktop_action_name = "None"
                is_desktop = self.mode_manager and self.mode_manager.is_desktop_active

                rejection_reason = "No hand detected"

                if result.hands:
                    pref_hand = getattr(self.profile_gesture_config, "steering_preferred_hand", "right")
                    primary_idx = select_primary_hand_index(result.hands, pref_hand)
                    if primary_idx is None:
                        primary_idx = 0

                    primary_hand = result.hands[primary_idx]

                    analyses = self.hand_analyzer.analyze_hands(result.hands)
                    gesture_results = self.gesture_manager.process_hands(analyses)

                    if gesture_results and primary_idx < len(gesture_results):
                        g0 = gesture_results[primary_idx]
                        if getattr(g0, "detected", False):
                            gesture_name = getattr(g0, "gesture_name", "None")
                            gesture_confidence = getattr(g0, "confidence", 0.0)
                            rejection_reason = "None"
                        else:
                            rejection_reason = getattr(g0, "rejection_reason", "No matching pose")
                    elif gesture_results:
                        g0 = gesture_results[0]
                        if getattr(g0, "detected", False):
                            gesture_name = getattr(g0, "gesture_name", "None")
                            gesture_confidence = getattr(g0, "confidence", 0.0)
                            rejection_reason = "None"
                        else:
                            rejection_reason = getattr(g0, "rejection_reason", "No matching pose")

                    if is_desktop and self.desktop_controller:
                        ordered_hands = [primary_hand] + [h for i, h in enumerate(result.hands) if i != primary_idx]
                        ordered_analyses = [analyses[primary_idx]] + [a for i, a in enumerate(analyses) if i != primary_idx]
                        ordered_gestures = [gesture_results[primary_idx]] + [g for i, g in enumerate(gesture_results) if i != primary_idx] if gesture_results else []
                        desk_telem = self.desktop_controller.process(ordered_hands, ordered_analyses, ordered_gestures)
                        desktop_action_name = desk_telem.get("desktop_action", "Idle")
                        action_name = desktop_action_name
                        # Reset controller output so virtual gamepad doesn't stick
                        action_state = self.action_engine.process([], [])
                        self.xbox_plugin.process(action_state)
                    else:
                        action_state = self.action_engine.process(gesture_results, analyses)
                        self.xbox_plugin.process(action_state)

                        norm_steering = getattr(action_state, "steering", 0.0)
                        raw_sensor = getattr(action_state, "raw_sensor_angle", 0.0)
                        adjusted_angle = getattr(action_state, "adjusted_steering_angle", norm_steering * 30.0)
                        steering_angle = adjusted_angle
                        raw_angle = raw_sensor

                        if abs(norm_steering) <= 0.03 or abs(adjusted_angle) <= 1.0:
                            direction = "CENTER"
                        elif norm_steering < -0.03:
                            direction = "LEFT"
                        else:
                            direction = "RIGHT"

                        if getattr(action_state, "accelerator", False):
                            action_name = "Accelerator"
                        elif getattr(action_state, "brake", False):
                            action_name = "Brake"
                        elif getattr(action_state, "handbrake", False):
                            action_name = "Handbrake"
                        elif abs(norm_steering) > 0.02:
                            action_name = "Steering"

                    hand0 = primary_hand
                    tracking_conf = float(getattr(hand0, "score", getattr(hand0, "confidence", 0.95)))
                else:
                    if is_desktop and self.desktop_controller:
                        self.desktop_controller.process([], [], [])
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

                proc_end_time = time.monotonic()
                proc_duration_ms = (proc_end_time - proc_start_time) * 1000.0
                e2e_latency_ms = (proc_end_time - cap_timestamp) * 1000.0
                cam_fps = self.async_capture.capture_fps if self.async_capture else 0.0
                dropped_frames = self.async_capture.dropped_frames if self.async_capture else 0
                mp_infer_ms = getattr(result, "inference_time_ms", 0.0)

                telemetry = {
                    "mode": self.mode_manager.active_mode.value if self.mode_manager else "driving",
                    "steering_angle": steering_angle,
                    "raw_steering": raw_angle,
                    "normalized_steering": norm_steering,
                    "direction": direction,
                    "gesture": gesture_name,
                    "gesture_confidence": gesture_confidence,
                    "tracking_confidence": tracking_conf,
                    "handedness_confidence": tracking_conf,
                    "rejection_reason": rejection_reason,
                    "action": action_name,
                    "desktop_action": desktop_action_name,
                    "camera_fps": cam_fps if cam_fps > 0.0 else self.fps_counter.fps,
                    "processing_fps": self.fps_counter.fps,
                    "latency_ms": proc_duration_ms,
                    "capture_latency_ms": cap_to_proc_latency_ms,
                    "end_to_end_latency_ms": e2e_latency_ms,
                    "inference_time_ms": mp_infer_ms,
                    "dropped_frames": dropped_frames,
                    "tracking_confidence": tracking_conf,
                    "controller_status": ctrl_status_str,
                    "left_stick_x": stick_x,
                    "accelerator_rt": rt_val,
                    "brake_lt": lt_val,
                    "buttons_pressed": buttons_pressed,
                    "camera_name": "Integrated Webcam",
                    "profile_name": self.profile_name,
                    "calibration_snapshot": cal_snap,
                }

                self.frame_processed.emit(result.annotated_image, self.fps_counter.fps, telemetry)

        finally:
            self._cleanup_resources()

    def _cleanup_resources(self) -> None:
        """Release camera, tracker, and controller resources cleanly."""
        if self.async_capture:
            try:
                self.async_capture.stop()
            except Exception as exc:
                logger.warning("Error stopping async capture: %s", exc)

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

        if self.desktop_controller:
            try:
                self.desktop_controller.reset()
            except Exception as exc:
                logger.warning("Error resetting desktop controller: %s", exc)

        self.status_changed.emit("Camera", "Stopped", "neutral")
        self.status_changed.emit("MediaPipe", "Idle", "neutral")
        self.status_changed.emit("Controller", "Disconnected", "neutral")
        logger.info("PipelineWorker resources released cleanly.")
