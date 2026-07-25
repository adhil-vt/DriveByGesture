"""
gesturedrive.camera.demo
=========================
Standalone camera test / demonstration application.

Purpose
-------
Verifies that the camera subsystem works correctly in isolation —
completely independent of hand tracking, gesture recognition,
controller output, or any other GestureDrive subsystem.

Usage
-----
    python -m camera.demo                  # use default camera (index 0)
    python -m camera.demo --index 1        # use a specific camera index
    python -m camera.demo --list           # list all available cameras
    python -m camera.demo --width 1280 --height 720 --fps 30

Controls
--------
    Q   — quit and release all resources

Overlay
-------
The live feed renders the following information on every frame:
    - Measured FPS (rolling 60-frame window)
    - Frame resolution (width × height)
    - Camera index
    - OpenCV backend name
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from collections import deque
from pathlib import Path
from typing import Deque

# Allow running as ``python -m camera.demo`` from the project root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cv2

from camera.camera import CameraEnumerator, CameraInfo, OpenCVCameraSource
from config.schema import CameraConfig
from core.exceptions import CaptureError
from logging_system.handlers import make_console_handler

# ── Logging setup ──────────────────────────────────────────────────────────────

logging.getLogger().addHandler(make_console_handler(level="DEBUG"))
logging.getLogger().setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)


# ── Overlay rendering ──────────────────────────────────────────────────────────

# OpenCV font / color constants — kept as module-level so they are defined
# once and referenced by _draw_overlay().
_FONT = cv2.FONT_HERSHEY_SIMPLEX
_FONT_SCALE_MAIN: float = 0.65
_FONT_SCALE_SMALL: float = 0.50
_FONT_THICKNESS: int = 1
_COLOR_GREEN = (0, 220, 0)
_COLOR_WHITE = (255, 255, 255)
_COLOR_SHADOW = (0, 0, 0)
_LINE_HEIGHT: int = 26
_PADDING: int = 12


def _draw_text_with_shadow(
    frame,
    text: str,
    x: int,
    y: int,
    scale: float,
    color: tuple,
) -> None:
    """
    Render ``text`` at ``(x, y)`` with a 1-pixel black drop-shadow for
    legibility on any background colour.

    Parameters
    ----------
    frame:
        The BGR numpy array to draw on (modified in-place).
    text:
        The string to render.
    x, y:
        Top-left anchor position in pixels.
    scale:
        Font scale factor.
    color:
        BGR text colour.
    """
    # Shadow
    cv2.putText(
        frame, text, (x + 1, y + 1),
        _FONT, scale, _COLOR_SHADOW, _FONT_THICKNESS + 1, cv2.LINE_AA,
    )
    # Main text
    cv2.putText(
        frame, text, (x, y),
        _FONT, scale, color, _FONT_THICKNESS, cv2.LINE_AA,
    )


def _draw_overlay(
    frame,
    measured_fps: float,
    width: int,
    height: int,
    camera_index: int,
    backend: str,
) -> None:
    """
    Render the diagnostic overlay onto ``frame`` in-place.

    Parameters
    ----------
    frame:
        BGR image array (modified in-place).
    measured_fps:
        Rolling FPS calculated from recent frame timestamps.
    width:
        Actual frame width in pixels.
    height:
        Actual frame height in pixels.
    camera_index:
        Integer device index of the active camera.
    backend:
        OpenCV backend name string.
    """
    lines = [
        (f"FPS: {measured_fps:5.1f}", _COLOR_GREEN, _FONT_SCALE_MAIN),
        (f"Resolution: {width} x {height}", _COLOR_WHITE, _FONT_SCALE_SMALL),
        (f"Camera index: {camera_index}", _COLOR_WHITE, _FONT_SCALE_SMALL),
        (f"Backend: {backend}", _COLOR_WHITE, _FONT_SCALE_SMALL),
    ]

    y = _PADDING + _LINE_HEIGHT
    for text, color, scale in lines:
        _draw_text_with_shadow(frame, text, _PADDING, y, scale, color)
        y += _LINE_HEIGHT

    # Bottom hint
    hint = "Press Q to quit"
    _draw_text_with_shadow(frame, hint, _PADDING, height - _PADDING, _FONT_SCALE_SMALL, _COLOR_WHITE)


# ── FPS measurement ────────────────────────────────────────────────────────────

class _RollingFPSCounter:
    """
    Lightweight rolling-window FPS counter.

    Keeps the last ``window`` frame timestamps and computes FPS as
    ``(window - 1) / (newest - oldest)``.

    Parameters
    ----------
    window:
        Number of timestamps to retain (default 60).
    """

    def __init__(self, window: int = 60) -> None:
        self._timestamps: Deque[float] = deque(maxlen=window)

    def tick(self) -> None:
        """Record the current monotonic timestamp."""
        self._timestamps.append(time.monotonic())

    @property
    def fps(self) -> float:
        """Current FPS, or 0.0 if fewer than 2 ticks have been recorded."""
        if len(self._timestamps) < 2:
            return 0.0
        elapsed = self._timestamps[-1] - self._timestamps[0]
        if elapsed <= 0.0:
            return 0.0
        return (len(self._timestamps) - 1) / elapsed


# ── CLI helpers ────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the demo."""
    parser = argparse.ArgumentParser(
        prog="python -m camera.demo",
        description="GestureDrive — Camera subsystem demo.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available cameras and exit.",
    )
    parser.add_argument(
        "--index",
        type=int,
        default=None,
        metavar="N",
        help="Camera device index to open (default: from config).",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=None,
        metavar="PX",
        help="Desired frame width in pixels (default: from config).",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=None,
        metavar="PX",
        help="Desired frame height in pixels (default: from config).",
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=None,
        metavar="FPS",
        help="Desired target FPS (default: from config).",
    )
    return parser.parse_args()


def _list_cameras() -> None:
    """Print information about all discoverable cameras to stdout."""
    enumerator = CameraEnumerator()
    cameras = enumerator.enumerate()

    if not cameras:
        print("No cameras found.")
        return

    print(f"{'Index':>6}  {'Resolution':>14}  {'FPS':>6}  Backend")
    print("-" * 46)
    for cam in cameras:
        print(
            f"{cam.index:>6}  "
            f"{cam.width:>5}x{cam.height:<5}  "
            f"{cam.fps:>6.1f}  "
            f"{cam.backend}"
        )


# ── Main demo loop ─────────────────────────────────────────────────────────────

def _build_camera(args: argparse.Namespace) -> OpenCVCameraSource:
    """
    Construct an ``OpenCVCameraSource`` from CLI arguments, falling back to
    ``CameraConfig`` defaults for any unspecified arguments.

    Parameters
    ----------
    args:
        Parsed CLI namespace.

    Returns
    -------
    OpenCVCameraSource
        Not yet opened.
    """
    defaults = CameraConfig()
    return OpenCVCameraSource(
        device_index=args.index  if args.index  is not None else defaults.device_index,
        target_width=args.width  if args.width  is not None else defaults.width,
        target_height=args.height if args.height is not None else defaults.height,
        target_fps=args.fps    if args.fps    is not None else defaults.fps,
    )


def run_demo(args: argparse.Namespace) -> int:
    """
    Open the camera and run the live display loop.

    Parameters
    ----------
    args:
        Parsed CLI namespace.

    Returns
    -------
    int
        Exit code: 0 for clean exit, 1 on error.
    """
    camera = _build_camera(args)
    fps_counter = _RollingFPSCounter(window=60)
    window_name = "GestureDrive — Camera Demo (Q to quit)"

    try:
        camera.open()
    except CaptureError as exc:
        logger.error("Could not open camera: %s", exc)
        return 1

    logger.info(
        "Demo started. Camera: index=%r, %dx%d @ %.1f fps, backend=%s.",
        camera.device_index,
        *camera.resolution,
        camera.fps,
        camera.backend,
    )

    width, height = camera.resolution
    exit_code = 0

    try:
        while True:
            try:
                frame = camera.read()
            except CaptureError as exc:
                logger.error("Frame read error: %s", exc)
                exit_code = 1
                break

            fps_counter.tick()
            image = frame.image  # numpy ndarray (BGR)

            _draw_overlay(
                frame=image,
                measured_fps=fps_counter.fps,
                width=width,
                height=height,
                camera_index=int(camera.device_index),
                backend=camera.backend,
            )

            cv2.imshow(window_name, image)

            # Wait 1 ms; check for 'Q' or window-close event.
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q") or key == ord("Q"):
                logger.info("User pressed Q — shutting down demo.")
                break

            # Also detect if the user closed the window via the OS title bar.
            if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
                logger.info("Window closed by user — shutting down demo.")
                break

    finally:
        camera.release()
        cv2.destroyAllWindows()
        logger.info("All resources released. Demo exited cleanly.")

    return exit_code


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    """Main entry point for ``python -m camera.demo``."""
    args = _parse_args()

    if args.list:
        _list_cameras()
        sys.exit(0)

    sys.exit(run_demo(args))


if __name__ == "__main__":
    main()
