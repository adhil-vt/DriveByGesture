"""
gesturedrive.gesture.result
=============================
Re-exports GestureResult and GestureResultSet from core.models.

This shim keeps gesture-layer imports clean and avoids authors needing
to know where in core/ the models are defined.
"""

from core.models import GestureResult, GestureResultSet  # noqa: F401

__all__ = ["GestureResult", "GestureResultSet"]
