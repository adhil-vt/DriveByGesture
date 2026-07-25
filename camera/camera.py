"""
gesturedrive.input_capture.camera
===================================
ICameraSource abstraction and its OpenCV-backed implementation.

Classes
-------
CameraInfo
    Value object describing a discovered camera device.
CameraEnumerator
    Utility for probing available camera devices by index.
OpenCVCameraSource
    Production implementation using ``cv2.VideoCapture``.
    Reads frames from a local webcam device by index or a video file path.

Notes
-----
- All OpenCV import is isolated to this module.
- The rest of the system depends only on ``ICameraSource`` (from core).
- To add a new camera backend (e.g., GStreamer, IP camera), implement
  ``ICameraSource`` in a new module and inject it in ``app.py``.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import List, Optional, Union

import cv2

from config.schema import CameraConfig
from core.exceptions import CaptureError
from core.interfaces import ICameraSource
from core.models import Frame

logger = logging.getLogger(__name__)


# ── Value objects ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class CameraInfo:
    """
    Describes a discovered camera device.

    Attributes
    ----------
    index:
        Integer device index used to open the camera via cv2.VideoCapture.
    width:
        Actual frame width in pixels reported by the driver after opening.
    height:
        Actual frame height in pixels reported by the driver after opening.
    fps:
        Actual frames-per-second reported by the driver after opening.
    backend:
        OpenCV backend name string, e.g. ``"DSHOW"`` or ``"V4L2"``.
    """

    index: int
    width: int
    height: int
    fps: float
    backend: str


# ── Camera enumeration ─────────────────────────────────────────────────────────

class CameraEnumerator:
    """
    Probes integer device indices to discover available camera devices.

    Design notes
    ------------
    - Probing stops at the first index that fails to open, up to ``max_probe``.
    - Each probe attempt is released immediately after reading properties so
      no device is held open longer than necessary.
    - Thread-safe: each call to ``enumerate()`` is independent and stateless.

    Parameters
    ----------
    max_probe:
        Maximum number of device indices to probe (0 … max_probe-1).
    """

    _DEFAULT_MAX_PROBE: int = 8

    def __init__(self, max_probe: int = _DEFAULT_MAX_PROBE) -> None:
        self._max_probe = max_probe

    def enumerate(self) -> List[CameraInfo]:
        """
        Return a list of ``CameraInfo`` objects for every reachable camera.

        Returns
        -------
        List[CameraInfo]
            Ordered by device index.  Empty list if no cameras are found.
        """
        found: List[CameraInfo] = []

        for idx in range(self._max_probe):
            cap = cv2.VideoCapture(idx)
            if not cap.isOpened():
                cap.release()
                # Indices are not guaranteed contiguous; keep probing.
                logger.debug("CameraEnumerator: index %d not available.", idx)
                continue

            info = CameraInfo(
                index=idx,
                width=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                height=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                fps=cap.get(cv2.CAP_PROP_FPS),
                backend=cap.getBackendName(),
            )
            found.append(info)
            cap.release()
            logger.debug(
                "CameraEnumerator: found camera at index %d (%dx%d @ %.1f fps, backend=%s).",
                idx, info.width, info.height, info.fps, info.backend,
            )

        logger.info("CameraEnumerator: %d camera(s) found.", len(found))
        return found


# ── OpenCV camera source ───────────────────────────────────────────────────────

class OpenCVCameraSource(ICameraSource):
    """
    ICameraSource implementation backed by OpenCV's VideoCapture.

    Parameters
    ----------
    device_index:
        Integer device index (0 = default webcam) or path to a video file.
    target_width:
        Desired frame width in pixels. Camera may not honour this exactly.
    target_height:
        Desired frame height in pixels.
    target_fps:
        Desired frames per second. Camera may cap this.

    Raises
    ------
    CaptureError
        On ``open()`` if the device cannot be accessed, or on ``read()`` if
        a frame cannot be retrieved.

    Thread safety
    -------------
    ``open()``, ``release()``, and ``read()`` are protected by an internal
    ``threading.Lock``.  It is safe to call ``release()`` from a different
    thread than the one calling ``read()``.
    """

    def __init__(
        self,
        device_index: Union[int, str] = 0,
        target_width: int = 1280,
        target_height: int = 720,
        target_fps: float = 30.0,
    ) -> None:
        self._device_index = device_index
        self._target_width = target_width
        self._target_height = target_height
        self._target_fps = target_fps

        self._capture: Optional[cv2.VideoCapture] = None
        self._lock = threading.Lock()
        self._seq_id: int = 0
        self._actual_width: int = 0
        self._actual_height: int = 0
        self._actual_fps: float = 0.0
        self._backend: str = ""

    # ── ICameraSource ──────────────────────────────────────────────────────────

    def open(self) -> None:
        """
        Open the camera device and apply the requested resolution and FPS.

        The camera is opened with the platform-default backend.  Resolution
        and FPS hints are written via ``CAP_PROP_*``; the driver may silently
        clamp them to its supported range, so actual values are read back and
        stored in ``_actual_*``.

        Raises
        ------
        CaptureError
            If the device index is invalid, the camera is already opened, or
            the VideoCapture cannot be initialised.
        """
        with self._lock:
            if self._capture is not None and self._capture.isOpened():
                raise CaptureError(
                    f"Camera at index {self._device_index!r} is already open. "
                    "Call release() before re-opening."
                )

            logger.debug(
                "Opening camera index=%r at %dx%d @ %.1f fps.",
                self._device_index, self._target_width,
                self._target_height, self._target_fps,
            )

            cap = cv2.VideoCapture(self._device_index)

            if not cap.isOpened():
                cap.release()
                raise CaptureError(
                    f"Failed to open camera at index {self._device_index!r}. "
                    "Device may be unavailable or the index is invalid."
                )

            # Apply requested hints — driver is free to ignore them.
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._target_width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._target_height)
            cap.set(cv2.CAP_PROP_FPS, self._target_fps)

            # Read back the values the driver actually accepted.
            self._actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self._actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self._actual_fps = cap.get(cv2.CAP_PROP_FPS)
            self._backend = cap.getBackendName()

            self._capture = cap
            self._seq_id = 0

        logger.info(
            "Camera opened: index=%r, resolution=%dx%d, fps=%.1f, backend=%s.",
            self._device_index,
            self._actual_width,
            self._actual_height,
            self._actual_fps,
            self._backend,
        )

    def read(self) -> Frame:
        """
        Capture and return a single frame.

        Returns
        -------
        Frame
            Raw BGR image (numpy ndarray), Unix timestamp, monotonic seq_id,
            and actual width/height.

        Raises
        ------
        CaptureError
            If the camera is not open, the device has been disconnected, or
            the frame cannot be decoded.
        """
        with self._lock:
            if self._capture is None or not self._capture.isOpened():
                raise CaptureError(
                    "Cannot read: camera is not open. Call open() first."
                )

            ok, image = self._capture.read()

        if not ok or image is None:
            logger.error(
                "Frame read failure on camera index=%r (seq_id=%d). "
                "Device may have been disconnected.",
                self._device_index,
                self._seq_id,
            )
            raise CaptureError(
                f"Failed to read frame from camera index={self._device_index!r}. "
                "Camera may have been disconnected."
            )

        self._seq_id += 1
        return Frame(
            image=image,
            timestamp=time.time(),
            seq_id=self._seq_id,
            width=self._actual_width,
            height=self._actual_height,
        )

    def release(self) -> None:
        """
        Release the VideoCapture device and free all associated resources.

        Safe to call even if the camera is already closed; no-op in that case.
        """
        with self._lock:
            if self._capture is None:
                return

            self._capture.release()
            self._capture = None

        logger.info(
            "Camera closed: index=%r.",
            self._device_index,
        )

    @property
    def is_open(self) -> bool:
        """Return True if the VideoCapture is initialised and currently open."""
        with self._lock:
            return self._capture is not None and self._capture.isOpened()

    @property
    def fps(self) -> float:
        """Actual FPS reported by the camera driver after ``open()``."""
        return self._actual_fps

    @property
    def resolution(self) -> tuple[int, int]:
        """Actual ``(width, height)`` in pixels after ``open()``."""
        return (self._actual_width, self._actual_height)

    @property
    def device_index(self) -> Union[int, str]:
        """The device index or path used to open this camera."""
        return self._device_index

    @property
    def backend(self) -> str:
        """OpenCV backend name, e.g. ``"DSHOW"`` or ``"V4L2"``."""
        return self._backend

    # ── Context manager support ────────────────────────────────────────────────

    def __enter__(self) -> "OpenCVCameraSource":
        """Open the camera when used as a context manager."""
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Release the camera on context manager exit, even if an exception occurred."""
        self.release()

    # ── Factory helper ─────────────────────────────────────────────────────────

    @classmethod
    def from_config(cls, config: CameraConfig) -> "OpenCVCameraSource":
        """
        Construct an ``OpenCVCameraSource`` from a ``CameraConfig``.

        This is the preferred construction path in the production wiring
        (``app.py``) so no configuration values are hardcoded at call sites.

        Parameters
        ----------
        config:
            A ``CameraConfig`` section from the loaded ``AppConfig``.

        Returns
        -------
        OpenCVCameraSource
            Configured but NOT yet opened (call ``open()`` separately).
        """
        return cls(
            device_index=config.device_index,
            target_width=config.width,
            target_height=config.height,
            target_fps=config.fps,
        )
