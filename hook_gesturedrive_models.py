"""
PyInstaller Runtime Hook — DriveByGesture model path fix.

tracking.hand_tracker uses Path(__file__).resolve().parent.parent / "models"
to locate hand_landmarker.task.  Inside a frozen PyInstaller bundle __file__
does not point to the source tree; it points into the ephemeral extraction
directory.  This hook patches _DEFAULT_MODEL_DIR to use sys._MEIPASS so the
model is found correctly regardless of where the EXE is launched from.

This file is referenced by DriveByGesture.spec under runtime_hooks=[].
"""
from __future__ import annotations

import sys
from pathlib import Path

if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    import tracking.hand_tracker as _ht

    _ht._DEFAULT_MODEL_DIR = Path(sys._MEIPASS) / "models"
