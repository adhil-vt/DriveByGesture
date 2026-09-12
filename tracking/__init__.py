"""
gesturedrive.tracking
======================
Hand tracking layer — wraps MediaPipe Hands and normalizes landmarks into domain HandState objects.
"""

from tracking.hand_selection import select_primary_hand, select_primary_hand_index
from tracking.hand_state import BoundingBox, HandState, Landmark, TrackingService
from tracking.hand_tracker import DetectedHand, MediaPipeHandTracker, TrackingResult
from tracking.landmark_normalizer import LandmarkNormalizer

__all__ = [
    "BoundingBox",
    "DetectedHand",
    "HandState",
    "Landmark",
    "LandmarkNormalizer",
    "MediaPipeHandTracker",
    "TrackingResult",
    "TrackingService",
    "select_primary_hand",
    "select_primary_hand_index",
]

