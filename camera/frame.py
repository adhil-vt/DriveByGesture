"""
gesturedrive.input_capture.frame
==================================
Re-exports the ``Frame`` model for convenient import from this layer.

``Frame`` is defined in ``core.models`` (the dependency-inversion root).
This shim allows code within ``input_capture`` to import from a local
relative path while obeying the one-way dependency rule.
"""

from core.models import Frame  # noqa: F401  (re-export)

__all__ = ["Frame"]
