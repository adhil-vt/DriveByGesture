"""
gesturedrive.tracking.demo
===========================
End-to-End Real-Time Pipeline Demonstration Application.

Pipeline
--------
Camera Module (OpenCVCameraSource)
    ↓  Frame
MediaPipeHandTracker
    ↓  TrackingResult
HandAnalyzer
    ↓  List[HandAnalysis]
GestureManager (Producer)
    ↓  List[GestureResult] & ActiveGesture
ActionEngine (Abstract Action Mapping)
    ↓  ActionState
XboxOutputPlugin (Hardware Controller Mapping)
    ↓  VirtualXboxController (vgamepad / ViGEmBus or NullController)
Windows OS & OpenCV Visualization Overlay

Purpose
-------
Runs the complete GestureDrive real-time control pipeline from camera input
to virtual Xbox controller output and visual HUD overlay.

Usage
-----
    python -m tracking.demo                   # default camera (index 0)
    python -m tracking.demo --index 1         # specific camera index
    python -m tracking.demo --hands 1         # detect only one hand
    python -m tracking.demo --complexity 0    # lite model (faster)

Controls
--------
    Q   — quit and release all resources cleanly
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from collections import deque
from pathlib import Path
from typing import Deque, List, Optional

# Allow ``python -m tracking.demo`` from the project root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cv2

from actions import ActionEngine, ActionState, ActionType
from calibration.calibration_manager import CalibrationManager
from calibration.calibration_overlay import render_calibration_overlay
from calibration.calibration_session import CalibrationStep
from camera.camera import OpenCVCameraSource
from config.schema import CameraConfig, GestureConfig, TrackingConfig
from controller import NullController, IVirtualController, VirtualXboxController, XboxController, XboxOutputPlugin
from core.exceptions import CaptureError, ControllerError, TrackingError
from core.models import Handedness
from logging_system.handlers import make_console_handler
from analysis import HandAnalysis, HandAnalyzer
from analysis.finger_state import FingerPosition
from gestures.manager import ActiveGesture, GestureManager
from gestures.registry import GestureRegistry
from gestures.builtins import (
    FistGesture,
    OpenPalmGesture,
    PeaceGesture,
    PinchGesture,
    PointGesture,
    ThumbsUpGesture,
)
from gestures.builtins.utils import calculate_pinch_signals
from tracking.hand_tracker import DetectedHand, MediaPipeHandTracker, TrackingResult

# ── Logging setup ──────────────────────────────────────────────────────────────

logging.getLogger().addHandler(make_console_handler(level="DEBUG"))
logging.getLogger().setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)


# ── Overlay constants ──────────────────────────────────────────────────────────

_FONT = cv2.FONT_HERSHEY_SIMPLEX
_COLOR_FPS        = (0, 230, 0)      # green
_COLOR_HAND_COUNT = (255, 220, 0)    # gold
_COLOR_LEFT_INFO  = (0, 200, 255)    # amber
_COLOR_RIGHT_INFO = (0, 255, 100)    # green
_COLOR_WHITE      = (255, 255, 255)
_COLOR_SHADOW     = (0, 0, 0)
_COLOR_BG         = (20, 20, 20)

_FONT_SCALE_LARGE: float  = 0.70
_FONT_SCALE_NORMAL: float = 0.60
_FONT_SCALE_SMALL: float  = 0.50
_THICKNESS: int = 1
_LINE_H: int = 28
_PAD: int = 12


# ── Rolling FPS counter ────────────────────────────────────────────────────────

class _RollingFPS:
    """Rolling-window FPS counter."""

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


# ── Overlay rendering ──────────────────────────────────────────────────────────

def _put(image, text: str, x: int, y: int, scale: float, color: tuple) -> None:
    """Draw text with a 1-pixel drop-shadow for legibility on any background."""
    cv2.putText(image, text, (x + 1, y + 1), _FONT, scale,
                _COLOR_SHADOW, _THICKNESS + 1, cv2.LINE_AA)
    cv2.putText(image, text, (x, y), _FONT, scale, color, _THICKNESS, cv2.LINE_AA)


def _draw_hud(
    image,
    fps: float,
    result: TrackingResult,
    action_state: Optional[ActionState] = None,
    controller: Optional[IVirtualController] = None,
    calibration_manager: Optional[CalibrationManager] = None,
) -> None:
    """Render top-left HUD overlay showing FPS, hand count, calibration status, and pipeline controls."""
    h, w = image.shape[:2]

    # Top-left panel
    y = _PAD + _LINE_H
    _put(image, f"FPS: {fps:5.1f}", _PAD, y, _FONT_SCALE_LARGE, _COLOR_FPS)
    y += _LINE_H

    hand_str = f"Hands: {result.hand_count}"
    _put(image, hand_str, _PAD, y, _FONT_SCALE_NORMAL, _COLOR_HAND_COUNT)
    y += int(_LINE_H * 1.2)

    for i, dh in enumerate(result.hands):
        color = _COLOR_LEFT_INFO if dh.handedness == Handedness.LEFT else _COLOR_RIGHT_INFO
        label = f"Hand {i + 1}: {dh.handedness.name:<5}  conf {dh.confidence:.0%}"
        _put(image, label, _PAD, y, _FONT_SCALE_SMALL, color)
        y += _LINE_H

    # Calibration Status line
    if calibration_manager is not None:
        cal_active = calibration_manager.active_calibration is not None
        cal_str = "Loaded" if cal_active else "Default"
        cal_color = (0, 255, 120) if cal_active else (200, 200, 200)
        _put(image, f"Calibration: {cal_str}", _PAD, y, _FONT_SCALE_SMALL, cal_color)
        y += _LINE_H

    # Bottom-left hint
    if calibration_manager is not None and calibration_manager.is_session_active:
        _put(image, "[ESC] Cancel Calibration | [Q] Quit", _PAD, h - _PAD, _FONT_SCALE_SMALL, _COLOR_WHITE)
    else:
        _put(image, "[C] Calibrate | [R] Reset | [Q] Quit", _PAD, h - _PAD, _FONT_SCALE_SMALL, _COLOR_WHITE)


def _draw_gesture_display_panels(
    image,
    analyses: List[HandAnalysis],
    gesture_manager: GestureManager,
    action_state: Optional[ActionState] = None,
    controller: Optional[IVirtualController] = None,
) -> None:
    """
    Display visual overlay panels showing ActiveGesture outputs, ActionState,
    Virtual Controller hardware state, and Pinch Debug metrics for every detected hand.

    Parameters
    ----------
    image:
        BGR numpy array (modified in-place).
    analyses:
        List of HandAnalysis results for hands in the current frame.
    gesture_manager:
        Active GestureManager instance.
    action_state:
        Current frame ActionState produced by ActionEngine.
    controller:
        Active IVirtualController instance.
    """
    if not analyses:
        return

    h, w = image.shape[:2]
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale_header = 0.46
    font_scale_val = 0.42
    thickness = 1
    line_h = 15
    padding = 8
    bg_color = (20, 20, 20)
    border_color = (0, 180, 0)
    color_title = (0, 255, 255)
    color_text = (255, 255, 255)
    color_gesture = (0, 255, 120)
    color_action = (255, 180, 0)
    color_ctrl = (0, 220, 255)
    color_pass = (0, 255, 0)
    color_fail = (0, 0, 255)

    pinch_gesture = gesture_manager.registry.get("Pinch")
    pinch_config = gesture_manager.config

    for analysis in analyses:
        hand_name = analysis.hand_state.handedness.name.upper()
        active_gesture = gesture_manager.get_active_gesture(hand_name)

        cooldown_str = (
            "Ready"
            if active_gesture.is_cooldown_ready
            else f"{active_gesture.cooldown_remaining:.2f}s"
        )

        lines = [
            (f"{hand_name} HAND", color_title, font_scale_header),
            ("Gesture:", color_text, font_scale_val),
            (active_gesture.current_gesture.upper(), color_gesture, font_scale_header),
            ("Confidence:", color_text, font_scale_val),
            (f"{active_gesture.confidence:.2f}", color_text, font_scale_val),
            ("Stable Frames:", color_text, font_scale_val),
            (f"{active_gesture.frames_stable}", color_text, font_scale_val),
            ("Cooldown:", color_text, font_scale_val),
            (cooldown_str, color_text, font_scale_val),
            ("----------------", (100, 100, 100), font_scale_val),
        ]

        # ── Action State & Steering Diagnostics Section ───────────────────────────────
        if action_state is not None:
            accel_str = "ON" if action_state.accelerator else "OFF"
            brake_str = "ON" if action_state.brake else "OFF"
            hb_str = "ON" if action_state.handbrake else "OFF"
            dz_active_str = "YES" if action_state.steering_deadzone_active else "NO"

            lines.extend([
                ("=== ACTION STATE ===", color_action, font_scale_header),
                (f"Accelerator: {accel_str}", color_pass if action_state.accelerator else color_text, font_scale_val),
                (f"Brake: {brake_str}", color_pass if action_state.brake else color_text, font_scale_val),
                (f"Handbrake: {hb_str}", color_pass if action_state.handbrake else color_text, font_scale_val),
                (f"Raw Steering: {action_state.raw_steering:+.2f}", color_text, font_scale_val),
                (f"Filtered Steering: {action_state.steering:+.2f}", color_text, font_scale_val),
                (f"Dead Zone Active: {dz_active_str}", color_pass if action_state.steering_deadzone_active else color_text, font_scale_val),
                (f"Sensitivity: {action_state.steering_sensitivity:.1f}", color_text, font_scale_val),
                (f"Curve Output: {action_state.steering_curve_output:+.2f}", color_text, font_scale_val),
                ("----------------", (100, 100, 100), font_scale_val),
            ])

        # ── Controller State Section ───────────────────────────────────────────
        if controller is not None and hasattr(controller, "_rt"):
            c_rt = getattr(controller, "_rt", 0)
            c_lt = getattr(controller, "_lt", 0)
            c_lx = getattr(controller, "_lx", 0)

            lines.extend([
                ("=== CONTROLLER STATE ===", color_ctrl, font_scale_header),
                (f"RT: {c_rt}", color_text, font_scale_val),
                (f"LT: {c_lt}", color_text, font_scale_val),
                (f"Left Stick X: {c_lx}", color_text, font_scale_val),
                ("----------------", (100, 100, 100), font_scale_val),
            ])

        # ── Pinch Debug Mode metrics ──────────────────────────────────────────
        signals = calculate_pinch_signals(analysis.hand_state) if hasattr(analysis, "hand_state") else None
        if signals and pinch_gesture:
            pinch_res = pinch_gesture.recognize(analysis)
            tip_tip = signals["tip_tip_dist"]
            tip_dip = signals["tip_dip_dist"]
            tip_mcp = signals["tip_mcp_dist"]
            alignment = signals["direction_alignment"]

            dist_pass = tip_tip <= pinch_config.pinch_max_normalized_distance
            align_pass = alignment >= 0.0 or tip_tip <= 0.25
            finger_pass = (
                analysis.index.position not in (FingerPosition.CURLED, FingerPosition.UNKNOWN)
                and analysis.middle.position != FingerPosition.UNKNOWN
                and analysis.ring.position not in (FingerPosition.EXTENDED, FingerPosition.UNKNOWN)
                and analysis.pinky.position not in (FingerPosition.EXTENDED, FingerPosition.UNKNOWN)
            )
            overall_pass = pinch_res.detected

            lines.extend([
                ("=== PINCH DEBUG ===", (0, 220, 255), font_scale_header),
                (f"ThumbTip-IndexTip Dist: {tip_tip:.3f}", color_text, font_scale_val),
                (f"ThumbTip-IndexDIP Dist: {tip_dip:.3f}", color_text, font_scale_val),
                (f"ThumbTip-IndexMCP Dist: {tip_mcp:.3f}", color_text, font_scale_val),
                (f"Norm Pinch Dist: {tip_tip:.3f}", color_text, font_scale_val),
                (f"Pinch Conf: {pinch_res.confidence:.2f}", color_text, font_scale_val),
                ("----------------", (100, 100, 100), font_scale_val),
                ("Distance Check:", color_text, font_scale_val),
                ("PASS" if dist_pass else "FAIL", color_pass if dist_pass else color_fail, font_scale_header),
                ("Vector Alignment:", color_text, font_scale_val),
                ("PASS" if align_pass else "FAIL", color_pass if align_pass else color_fail, font_scale_header),
                ("Finger States:", color_text, font_scale_val),
                ("PASS" if finger_pass else "FAIL", color_pass if finger_pass else color_fail, font_scale_header),
                ("Overall Result:", color_text, font_scale_val),
                ("PASS" if overall_pass else "FAIL", color_pass if overall_pass else color_fail, font_scale_header),
                ("----------------", (100, 100, 100), font_scale_val),
            ])

        lines.extend([
            ("Thumb:", color_text, font_scale_val),
            (analysis.thumb.position.name, color_text, font_scale_val),
            ("Index:", color_text, font_scale_val),
            (analysis.index.position.name, color_text, font_scale_val),
            ("Middle:", color_text, font_scale_val),
            (analysis.middle.position.name, color_text, font_scale_val),
            ("Ring:", color_text, font_scale_val),
            (analysis.ring.position.name, color_text, font_scale_val),
            ("Pinky:", color_text, font_scale_val),
            (analysis.pinky.position.name, color_text, font_scale_val),
        ])

        bbox = analysis.hand_state.bounding_box
        bbox_left_px = int(bbox.left * w)
        bbox_right_px = int(bbox.right * w)
        bbox_top_px = int(bbox.top * h)

        max_text_w = 0
        for text, _, scale in lines:
            (tw, _), _ = cv2.getTextSize(text, font, scale, thickness)
            if tw > max_text_w:
                max_text_w = tw

        panel_w = max_text_w + padding * 2
        panel_h = len(lines) * line_h + padding * 2

        panel_x = bbox_right_px + 10
        if panel_x + panel_w > w - 5:
            panel_x = bbox_left_px - panel_w - 10

        panel_x = max(5, min(panel_x, w - panel_w - 5))
        panel_y = max(5, min(bbox_top_px, h - panel_h - 5))

        x1, y1 = panel_x, panel_y
        x2, y2 = panel_x + panel_w, panel_y + panel_h
        cv2.rectangle(image, (x1, y1), (x2, y2), bg_color, -1)
        cv2.rectangle(image, (x1, y1), (x2, y2), border_color, 1)

        text_y = y1 + padding + 12
        for text, color, scale in lines:
            cv2.putText(
                image,
                text,
                (x1 + padding, text_y),
                font,
                scale,
                color,
                thickness,
                cv2.LINE_AA,
            )
            text_y += line_h


# ── CLI parsing ────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m tracking.demo",
        description="GestureDrive — End-to-End Real-Time Control Pipeline Demo.",
    )
    parser.add_argument(
        "--index", type=int, default=None, metavar="N",
        help="Camera device index (default: from config).",
    )
    parser.add_argument(
        "--width", type=int, default=None, metavar="PX",
        help="Desired frame width in pixels (default: from config).",
    )
    parser.add_argument(
        "--height", type=int, default=None, metavar="PX",
        help="Desired frame height in pixels (default: from config).",
    )
    parser.add_argument(
        "--fps", type=float, default=None, metavar="FPS",
        help="Desired target FPS (default: from config).",
    )
    parser.add_argument(
        "--hands", type=int, default=None, metavar="N",
        help="Maximum number of hands to track, 1 or 2 (default: from config).",
    )
    parser.add_argument(
        "--complexity", type=int, default=None, metavar="N",
        choices=[0, 1],
        help="MediaPipe model complexity: 0=lite, 1=full (default: from config).",
    )
    parser.add_argument(
        "--det-conf", type=float, default=None, metavar="F",
        help="Minimum detection confidence [0.0–1.0] (default: from config).",
    )
    parser.add_argument(
        "--track-conf", type=float, default=None, metavar="F",
        help="Minimum tracking confidence [0.0–1.0] (default: from config).",
    )
    return parser.parse_args()


def _build_camera(args: argparse.Namespace) -> OpenCVCameraSource:
    cam_cfg = CameraConfig()
    return OpenCVCameraSource(
        device_index=args.index if args.index is not None else cam_cfg.device_index,
        target_width=args.width if args.width is not None else cam_cfg.width,
        target_height=args.height if args.height is not None else cam_cfg.height,
        target_fps=args.fps if args.fps is not None else cam_cfg.fps,
    )


def _build_tracker(args: argparse.Namespace) -> MediaPipeHandTracker:
    trk_cfg = TrackingConfig()
    return MediaPipeHandTracker(
        max_num_hands=(
            args.hands if args.hands is not None else trk_cfg.max_num_hands
        ),
        min_detection_confidence=(
            args.det_conf if args.det_conf is not None
            else trk_cfg.min_detection_confidence
        ),
        min_tracking_confidence=(
            args.track_conf if args.track_conf is not None
            else trk_cfg.min_tracking_confidence
        ),
        model_complexity=(
            args.complexity if args.complexity is not None
            else trk_cfg.model_complexity
        ),
    )


def _build_gesture_manager() -> GestureManager:
    """Construct GestureManager pre-populated with built-in gestures using specificity priorities."""
    config = GestureConfig()
    registry = GestureRegistry()
    registry.register(OpenPalmGesture(priority=config.priority_open_palm))
    registry.register(PointGesture(priority=config.priority_point))
    registry.register(PeaceGesture(priority=config.priority_peace))
    registry.register(FistGesture(priority=config.priority_fist))
    registry.register(ThumbsUpGesture(priority=config.priority_thumbs_up))
    registry.register(PinchGesture(priority=config.priority_pinch, config=config))
    return GestureManager(registry=registry, config=config)


# ── Main demo loop ─────────────────────────────────────────────────────────────

def run_demo(args: argparse.Namespace) -> int:
    """
    Open camera and tracker, run real-time control pipeline from camera to Virtual Xbox Controller.
    """
    camera = _build_camera(args)
    tracker = _build_tracker(args)
    hand_analyzer = HandAnalyzer()
    gesture_manager = _build_gesture_manager()

    # End-to-End Pipeline Services: ActionEngine & Controller Output
    action_engine = ActionEngine()
    calibration_manager = CalibrationManager()
    calibration_manager.bind_steering_pipeline(action_engine)

    xbox_controller: IVirtualController = XboxController()
    try:
        xbox_controller.connect()
        logger.info("End-to-End Pipeline: XboxController connected via ViGEmBus.")
    except ControllerError as exc:
        logger.warning(
            "XboxController connect failed (%s). Falling back to NullController (safe mode).", exc
        )
        xbox_controller = NullController()
        xbox_controller.connect()

    xbox_plugin = XboxOutputPlugin(controller=xbox_controller)

    fps_counter = _RollingFPS(window=60)
    window_name = "GestureDrive — End-to-End Control Pipeline Demo (Q to quit)"

    try:
        camera.open()
    except CaptureError as exc:
        logger.error("Could not open camera: %s", exc)
        return 1

    logger.info(
        "Camera: index=%r, %dx%d @ %.1f fps, backend=%s.",
        camera.device_index, *camera.resolution, camera.fps, camera.backend,
    )

    try:
        tracker.initialise()
    except TrackingError as exc:
        logger.error("Could not initialise hand tracker: %s", exc)
        camera.release()
        return 1

    logger.info("Hand tracker initialised. Starting real-time control loop …")

    exit_code = 0

    try:
        while True:
            try:
                frame = camera.read()
            except CaptureError as exc:
                logger.error("Frame read error: %s", exc)
                exit_code = 1
                break

            try:
                result = tracker.process_frame(frame)
            except TrackingError as exc:
                logger.warning("Tracking error (frame %d): %s", frame.seq_id, exc)
                display = frame.image.copy()  # type: ignore[attr-defined]
                _put(display, "TRACKING ERROR", 20, 40, 0.8, (0, 0, 255))
                cv2.imshow(window_name, display)
                if (cv2.waitKey(1) & 0xFF) in (ord("q"), ord("Q")):
                    break
                continue

            fps_counter.tick()

            analyses: List[HandAnalysis] = []
            if result.hands:
                # 1. Analyze finger states & hand posture
                analyses = hand_analyzer.analyze_hands(result.hands)

                # 2. Process gestures through GestureManager (Producer)
                gesture_results = gesture_manager.process_hands(analyses)

                # 3. Process abstract actions via ActionEngine
                action_state = action_engine.process(gesture_results, analyses)

                # 4. Translate ActionState to Virtual Xbox Controller inputs
                xbox_plugin.process(action_state)

                # 5. Render visual display overlay
                _draw_gesture_display_panels(
                    result.annotated_image, analyses, gesture_manager, action_state, xbox_controller
                )
            else:
                # No hands detected -> send neutral state to ActionEngine & Controller
                action_state = action_engine.process([], [])
                xbox_plugin.process(action_state)

            # Interactive Calibration Wizard processing
            if calibration_manager.is_session_active:
                snap = calibration_manager.session.process_frame(analyses)
                render_calibration_overlay(result.annotated_image, snap)

            # Overlay HUD
            _draw_hud(result.annotated_image, fps_counter.fps, result, action_state, xbox_controller, calibration_manager)

            # Display frame
            cv2.imshow(window_name, result.annotated_image)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), ord("Q")):
                logger.info("User pressed Q — shutting down demo.")
                break
            elif key in (ord("s"), ord("S")):
                if calibration_manager.session.current_step == CalibrationStep.SUMMARY:
                    data = calibration_manager.accept_and_save_session()
                    if data is not None:
                        action_engine.steering_pipeline.set_calibration(data)
                        logger.info("Calibration Saved")
            elif key in (ord("c"), ord("C")):
                if not calibration_manager.is_session_active:
                    calibration_manager.start_session()
                    logger.info("Calibration Started")
            elif key in (ord("r"), ord("R")):
                if calibration_manager.session.current_step == CalibrationStep.SUMMARY:
                    calibration_manager.recalibrate()
                    logger.info("Recalibrating session from Step 1.")
                else:
                    msg = calibration_manager.reset_calibration()
                    action_engine.steering_pipeline.set_calibration(None)
                    logger.info(msg)
            elif key == 27:  # ESC key
                if calibration_manager.is_session_active:
                    msg = calibration_manager.cancel_session()
                    action_engine.steering_pipeline.set_calibration(calibration_manager.active_calibration)
                    logger.info(msg)

            if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
                logger.info("Window closed — shutting down demo.")
                break

    finally:
        tracker.shutdown()
        camera.release()
        xbox_controller.disconnect()
        cv2.destroyAllWindows()
        logger.info("All resources released. Demo exited cleanly.")

    return exit_code


def main() -> None:
    """Main entry point for ``python -m tracking.demo``."""
    sys.exit(run_demo(_parse_args()))


if __name__ == "__main__":
    main()
