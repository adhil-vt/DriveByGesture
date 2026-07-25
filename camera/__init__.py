"""
gesturedrive.input_capture
===========================
Webcam frame acquisition layer.

Responsibility
--------------
- Open and manage the physical camera device.
- Read raw frames at the configured FPS.
- Run the acquisition loop in a dedicated daemon thread.
- Publish ``FrameCapturedEvent`` to the EventBus for every new frame.

This package has NO knowledge of hand tracking, gesture recognition,
or controller output.

Public API
----------
    from camera import OpenCVCameraSource, CameraEnumerator, CameraInfo
    from camera import CaptureLoop
"""

from camera.camera import CameraEnumerator, CameraInfo, OpenCVCameraSource
from camera.capture_loop import CaptureLoop

__all__ = [
    "CameraEnumerator",
    "CameraInfo",
    "CaptureLoop",
    "OpenCVCameraSource",
]
