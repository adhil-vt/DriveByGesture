"""
gesturedrive.input_capture.capture_loop
=========================================
Background camera capture thread.

Responsibility
--------------
CaptureLoop runs ``ICameraSource.read()`` in a dedicated daemon thread and
publishes each captured frame as a ``FrameCapturedEvent`` on the EventBus.

Design notes
------------
- The thread is a daemon thread: it is automatically killed if the main
  process exits, preventing zombie threads.
- A ``threading.Event`` is used for clean shutdown signalling.
- Frame rate is throttled to the camera's configured FPS to avoid
  overwhelming downstream stages.
- If ``ICameraSource.read()`` fails, the loop retries up to
  ``max_retries`` times before publishing an ``ErrorEvent`` and stopping.
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime

from core.event_bus import EventBus
from core.events import ErrorEvent, FrameCapturedEvent
from core.exceptions import CaptureError
from core.interfaces import ICameraSource

logger = logging.getLogger(__name__)

_SOURCE_ID = "input_capture.capture_loop"


class CaptureLoop:
    """
    Runs camera capture in a background daemon thread.

    Parameters
    ----------
    camera:
        An opened ``ICameraSource`` instance.
    event_bus:
        The application-wide EventBus. Each frame is published here.
    max_retries:
        Number of consecutive read failures before the loop stops.

    Usage
    -----
        loop = CaptureLoop(camera=cam, event_bus=bus)
        loop.start()
        # ... application runs ...
        loop.stop()
    """

    def __init__(
        self,
        camera: ICameraSource,
        event_bus: EventBus,
        max_retries: int = 3,
    ) -> None:
        self._camera = camera
        self._bus = event_bus
        self._max_retries = max_retries

        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        """
        Start the capture daemon thread.

        Raises
        ------
        RuntimeError
            If the loop is already running.
        """
        if self._thread is not None and self._thread.is_alive():
            raise RuntimeError("CaptureLoop is already running.")

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="GestureDrive-CaptureLoop",
            daemon=True,
        )
        self._thread.start()
        logger.info("CaptureLoop started (camera fps=%.1f).", self._camera.fps)

    def stop(self) -> None:
        """
        Signal the capture thread to stop and wait for it to finish.

        Blocks for up to 2 seconds before returning regardless.
        """
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        logger.info("CaptureLoop stopped.")

    @property
    def is_running(self) -> bool:
        """Return True if the capture thread is currently alive."""
        return self._thread is not None and self._thread.is_alive()

    # ── Internal loop ─────────────────────────────────────────────────────────

    def _run(self) -> None:
        """
        Main loop executed on the daemon thread.

        Reads frames from the camera, publishes FrameCapturedEvent, and
        throttles to the camera's configured FPS.
        """
        consecutive_errors = 0
        frame_interval = 1.0 / max(self._camera.fps, 1.0)

        while not self._stop_event.is_set():
            loop_start = time.monotonic()

            try:
                frame = self._camera.read()
                consecutive_errors = 0

                self._bus.publish(
                    FrameCapturedEvent(
                        source=_SOURCE_ID,
                        frame=frame,
                    )
                )
            except CaptureError as exc:
                consecutive_errors += 1
                logger.warning(
                    "CaptureError (%d/%d): %s",
                    consecutive_errors,
                    self._max_retries,
                    exc,
                )
                if consecutive_errors >= self._max_retries:
                    self._bus.publish(
                        ErrorEvent(
                            source=_SOURCE_ID,
                            error=exc,
                            severity="error",
                            user_message=(
                                "Camera disconnected. "
                                "Please check your webcam and restart."
                            ),
                        )
                    )
                    logger.error("CaptureLoop stopping after %d retries.", self._max_retries)
                    break

            elapsed = time.monotonic() - loop_start
            sleep_time = frame_interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)
