"""
gesturedrive.gesture.recognizer_base
======================================
Re-exports IGestureRecognizer from core.interfaces as a convenience import.

This shim lets gesture authors write:
    from gesture.recognizer_base import IGestureRecognizer

instead of having to know the full core path.
"""

from core.interfaces import IGestureRecognizer  # noqa: F401

__all__ = ["IGestureRecognizer"]
