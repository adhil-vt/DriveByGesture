# gesture/custom/ — drop user-defined IGestureRecognizer classes here.
#
# Any .py file in this directory that contains a non-abstract subclass of
# IGestureRecognizer with a unique gesture_name will be auto-discovered by
# GestureRegistry on startup.
#
# Example minimal custom recognizer:
#
#   from gesture.recognizer_base import IGestureRecognizer
#   from core.models import GestureResult, HandState
#   from typing import Optional
#
#   class NitroRecognizer(IGestureRecognizer):
#       @property
#       def gesture_name(self) -> str:
#           return "nitro"
#
#       @property
#       def display_name(self) -> str:
#           return "Nitro Boost"
#
#       def recognize(self, hand_state, calibration=None):
#           # ... your detection logic ...
#           return GestureResult("nitro", confidence=0.9, value=None, active=True)
