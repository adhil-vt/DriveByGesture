"""
gesturedrive.camera.frame_buffer
=================================
Thread-safe LatestFrameBuffer and AsyncCameraCapture for real-time decoupled
camera acquisition and zero-stale-frame pipeline processing.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Optional

from core.exceptions import CaptureError
from core.interfaces import ICameraSource
from core.models import Frame

logger = logging.getLogger(__name__)


@dataclass
class FrameTiming:
    """
    Precision timestamps and latency metrics for a single frame lifecycle.
    """
    frame_seq: int
    capture_timestamp: float
    proc_start_timestamp: float = 0.0
    proc_end_timestamp: float = 0.0
    inference_time_ms: float = 0.0

    @property
    def capture_to_proc_latency_ms(self) -> float:
        """Latency from hardware frame capture to worker processing start (ms)."""
        if self.proc_start_timestamp > 0.0:
            return max(0.0, (self.proc_start_timestamp - self.capture_timestamp) * 1000.0)
        return 0.0

    @property
    def processing_duration_ms(self) -> float:
        """Time spent processing the frame through tracking, gestures, and actions (ms)."""
        if self.proc_end_timestamp > 0.0 and self.proc_start_timestamp > 0.0:
            return max(0.0, (self.proc_end_timestamp - self.proc_start_timestamp) * 1000.0)
        return 0.0

    @property
    def end_to_end_latency_ms(self) -> float:
        """Total elapsed time from camera capture to action dispatch completion (ms)."""
        if self.proc_end_timestamp > 0.0:
            return max(0.0, (self.proc_end_timestamp - self.capture_timestamp) * 1000.0)
        return 0.0


class LatestFrameBuffer:
    """
    Thread-safe single-slot frame buffer with condition variable signalling.

    Guarantees 'latest-frame-wins' semantics:
    - Publisher overwrites the single newest frame without blocking.
    - Dropped frame count is accurately tracked when a frame is superseded before consumption.
    - Consumer can block with a timeout waiting for the next fresh frame.
    - Zero stale frame accumulation in queues.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._condition = threading.Condition(self._lock)
        self._latest_frame: Optional[Frame] = None
        self._is_new: bool = False
        self._is_stopped: bool = False

        self._captured_count: int = 0
        self._dropped_count: int = 0
        self._consumed_count: int = 0

        self._fps_window_start: float = time.monotonic()
        self._fps_capture_count: int = 0
        self._current_capture_fps: float = 0.0

    def put(self, frame: Frame) -> None:
        """Publish newest frame into buffer, discarding previous unread frame if present."""
        now = time.monotonic()
        with self._condition:
            if self._is_new:
                self._dropped_count += 1

            self._latest_frame = frame
            self._is_new = True
            self._captured_count += 1
            self._fps_capture_count += 1

            # Update rolling capture FPS every 0.5s
            elapsed = now - self._fps_window_start
            if elapsed >= 0.5:
                self._current_capture_fps = self._fps_capture_count / elapsed
                self._fps_capture_count = 0
                self._fps_window_start = now

            self._condition.notify_all()

    def get(self, timeout: float = 0.1) -> Optional[Frame]:
        """Retrieve newest frame. Blocks up to ``timeout`` seconds for fresh frame."""
        with self._condition:
            while not self._is_new and not self._is_stopped:
                if not self._condition.wait(timeout=timeout):
                    return None
            if self._is_stopped:
                return None
            self._is_new = False
            self._consumed_count += 1
            return self._latest_frame

    def stop(self) -> None:
        """Signal buffer shutdown and unblock any waiting consumer."""
        with self._condition:
            self._is_stopped = True
            self._condition.notify_all()

    def reset(self) -> None:
        """Reset buffer counters and state."""
        with self._condition:
            self._latest_frame = None
            self._is_new = False
            self._is_stopped = False
            self._captured_count = 0
            self._dropped_count = 0
            self._consumed_count = 0
            self._fps_window_start = time.monotonic()
            self._fps_capture_count = 0
            self._current_capture_fps = 0.0

    @property
    def captured_count(self) -> int:
        with self._lock:
            return self._captured_count

    @property
    def dropped_count(self) -> int:
        with self._lock:
            return self._dropped_count

    @property
    def consumed_count(self) -> int:
        with self._lock:
            return self._consumed_count

    @property
    def capture_fps(self) -> float:
        with self._lock:
            return self._current_capture_fps


class AsyncCameraCapture:
    """
    Dedicated background capture manager (Thread A).
    Continuously acquires frames from an ICameraSource and feeds LatestFrameBuffer.
    """

    def __init__(self, camera: ICameraSource, frame_buffer: Optional[LatestFrameBuffer] = None) -> None:
        self.camera = camera
        self.buffer = frame_buffer or LatestFrameBuffer()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._last_error: Optional[Exception] = None

    def start(self) -> None:
        """Start the background camera capture thread."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self.buffer.reset()
        self._thread = threading.Thread(
            target=self._capture_loop,
            name="GestureDrive-AsyncCapture",
            daemon=True,
        )
        self._thread.start()
        logger.info("AsyncCameraCapture thread started.")

    def stop(self) -> None:
        """Stop background capture and release resources cleanly."""
        self._stop_event.set()
        self.buffer.stop()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None
        logger.info("AsyncCameraCapture thread stopped.")

    def get_latest_frame(self, timeout: float = 0.05) -> Optional[Frame]:
        """Fetch newest frame from buffer."""
        return self.buffer.get(timeout=timeout)

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def capture_fps(self) -> float:
        return self.buffer.capture_fps

    @property
    def dropped_frames(self) -> int:
        return self.buffer.dropped_count

    def _capture_loop(self) -> None:
        """Tight capture loop running exclusively on Thread A."""
        consecutive_errors = 0
        while not self._stop_event.is_set():
            try:
                frame = self.camera.read()
                frame.capture_timestamp = time.monotonic()
                self.buffer.put(frame)
                consecutive_errors = 0
            except CaptureError as exc:
                consecutive_errors += 1
                self._last_error = exc
                logger.warning("AsyncCameraCapture read error (%d): %s", consecutive_errors, exc)
                if consecutive_errors >= 5:
                    logger.error("AsyncCameraCapture: 5 consecutive capture failures; stopping loop.")
                    break
                time.sleep(0.01)
            except Exception as exc:
                logger.error("AsyncCameraCapture unexpected exception: %s", exc)
                self._last_error = exc
                break
