"""
gesturedrive.tracking.landmark_normalizer
==========================================
Normalizes MediaPipe raw landmarks into structured application HandState objects.
"""

from __future__ import annotations

import logging
from typing import List, Sequence, Tuple

from core.models import Handedness
from tracking.hand_state import BoundingBox, HandState, Landmark

logger = logging.getLogger(__name__)

_EXPECTED_LANDMARK_COUNT: int = 21
_PALM_LANDMARK_INDICES: Tuple[int, ...] = (0, 1, 5, 9, 13, 17)


class LandmarkNormalizer:
    """
    Processes raw MediaPipe landmark points into application domain ``HandState`` objects.

    Responsibilities
    ----------------
    - Accepts MediaPipe landmarks.
    - Validates that exactly 21 landmarks are present.
    - Converts landmarks into normalized ``Landmark`` objects.
    - Computes ``BoundingBox``.
    - Computes Palm Center (average of landmarks 0, 1, 5, 9, 13, 17).
    - Computes Hand Center (average of all 21 landmarks).
    - Preserves handedness and confidence.
    - Produces a complete ``HandState`` object.
    """

    def normalize(
        self,
        raw_landmarks: object,
        handedness: Handedness,
        confidence: float,
        timestamp: float = 0.0,
    ) -> HandState:
        """
        Convert raw MediaPipe landmarks into a ``HandState`` domain object.

        Parameters
        ----------
        raw_landmarks:
            MediaPipe landmark container or sequence (e.g. list of landmark objects
            with ``.x``, ``.y``, ``.z`` attributes or a ``NormalizedLandmarkList``).
        handedness:
            Parsed ``Handedness`` classification.
        confidence:
            Detection or tracking confidence score in [0.0, 1.0].
        timestamp:
            Timestamp of the frame capture.

        Returns
        -------
        HandState
            Immutable, fully populated HandState object.

        Raises
        ------
        ValueError
            If raw_landmarks does not contain exactly 21 landmark points.
        """
        if hasattr(raw_landmarks, "landmark"):
            lm_sequence = raw_landmarks.landmark  # type: ignore[attr-defined]
        else:
            lm_sequence = raw_landmarks

        count = len(lm_sequence)  # type: ignore[arg-type]
        if count != _EXPECTED_LANDMARK_COUNT:
            raise ValueError(
                f"Expected exactly {_EXPECTED_LANDMARK_COUNT} landmarks, got {count}."
            )

        landmarks: List[Landmark] = [
            Landmark(
                id=i,
                x=max(0.0, min(1.0, float(lm.x))),
                y=max(0.0, min(1.0, float(lm.y))),
                z=float(lm.z),
            )
            for i, lm in enumerate(lm_sequence)  # type: ignore[union-attr]
        ]

        bounding_box = self._calculate_bounding_box(landmarks)
        palm_center = self._calculate_palm_center(landmarks)
        hand_center = self._calculate_hand_center(landmarks)

        return HandState(
            handedness=handedness,
            confidence=confidence,
            landmarks=landmarks,
            bounding_box=bounding_box,
            palm_center=palm_center,
            hand_center=hand_center,
            timestamp=timestamp,
        )

    def normalize_task(
        self,
        lm_list: object,
        handedness: Handedness,
        confidence: float,
        timestamp: float = 0.0,
    ) -> HandState:
        """
        Alias for ``normalize`` to support MediaPipe Tasks API landmark lists.
        """
        return self.normalize(
            raw_landmarks=lm_list,
            handedness=handedness,
            confidence=confidence,
            timestamp=timestamp,
        )

    @staticmethod
    def _calculate_bounding_box(landmarks: Sequence[Landmark]) -> BoundingBox:
        """Calculate axis-aligned bounding box for the landmarks."""
        xs = [lm.x for lm in landmarks]
        ys = [lm.y for lm in landmarks]

        left = min(xs)
        right = max(xs)
        top = min(ys)
        bottom = max(ys)
        width = right - left
        height = bottom - top

        return BoundingBox(
            left=left,
            top=top,
            right=right,
            bottom=bottom,
            width=width,
            height=height,
        )

    @staticmethod
    def _calculate_palm_center(landmarks: Sequence[Landmark]) -> Tuple[float, float, float]:
        """Calculate palm center as average position of landmarks 0, 1, 5, 9, 13, 17."""
        palm_lms = [landmarks[idx] for idx in _PALM_LANDMARK_INDICES]
        n = float(len(_PALM_LANDMARK_INDICES))
        avg_x = sum(lm.x for lm in palm_lms) / n
        avg_y = sum(lm.y for lm in palm_lms) / n
        avg_z = sum(lm.z for lm in palm_lms) / n
        return (avg_x, avg_y, avg_z)

    @staticmethod
    def _calculate_hand_center(landmarks: Sequence[Landmark]) -> Tuple[float, float, float]:
        """Calculate hand center as average position of all 21 landmarks."""
        n = float(len(landmarks))
        avg_x = sum(lm.x for lm in landmarks) / n
        avg_y = sum(lm.y for lm in landmarks) / n
        avg_z = sum(lm.z for lm in landmarks) / n
        return (avg_x, avg_y, avg_z)

    @staticmethod
    def parse_handedness(mediapipe_classification: object) -> Handedness:
        """
        Convert MediaPipe's handedness classification label to Handedness enum.
        """
        try:
            label: str = mediapipe_classification.classification[0].label  # type: ignore[attr-defined]
        except (AttributeError, IndexError):
            return Handedness.UNKNOWN

        upper = label.strip().upper()
        if upper == "LEFT":
            return Handedness.LEFT
        if upper == "RIGHT":
            return Handedness.RIGHT
        return Handedness.UNKNOWN
