"""
gesturedrive.controller.controller_base
=========================================
Re-exports IVirtualController from core.interfaces.

Provides a clean local import path for controller-layer code.
"""

from core.interfaces import IVirtualController  # noqa: F401

__all__ = ["IVirtualController"]
