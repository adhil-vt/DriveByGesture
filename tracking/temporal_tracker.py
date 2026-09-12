"""
gesturedrive.tracking.temporal_tracker
======================================
Temporal hand tracking association and state isolation layer.

Responsibilities
----------------
1. Maintain stable hand_id association across consecutive frames despite MediaPipe detection order swaps.
2. Provide per-hand isolated HandednessStabilizer instances (preventing Left/Right cross-talk).
3. Provide per-hand isolated HandLandmarkFilter instances (preventing One Euro filter coordinate cross-talk).
4. Enforce strict track lifecycle (NEW, ACTIVE, TEMPORARILY_LOST, EXPIRED) with automatic cleanup.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Sequence, Tuple

from core.models import Handedness
from tracking.hand_state import BoundingBox, HandState, Landmark
from tracking.handedness_stabilizer import HandednessStabilizer
from tracking.landmark_filter import HandLandmarkFilter
from tracking.landmark_normalizer import LandmarkNormalizer

logger = logging.getLogger(__name__)


class TrackState(Enum):
    """Lifecycle state of a tracked physical hand."""
    NEW = auto()
    ACTIVE = auto()
    TEMPORARILY_LOST = auto()
    EXPIRED = auto()


@dataclass
class RawHandCandidate:
    """
    Unfiltered, un-associated candidate hand detection from MediaPipe and LandmarkNormalizer.
    """
    raw_landmarks: List[Landmark]
    raw_handedness: Handedness
    raw_confidence: float
    bounding_box: BoundingBox
    palm_center: Tuple[float, float, float]
    hand_center: Tuple[float, float, float]


class HandTrack:
    """
    State container for a single tracked physical hand.

    Maintains completely isolated handedness voting history and landmark filter states.
    """

    def __init__(
        self,
        track_id: int,
        initial_candidate: RawHandCandidate,
        timestamp: float,
        window_size: int = 7,
        switch_threshold: float = 0.65,
        min_cutoff: float = 1.0,
        beta: float = 0.007,
        d_cutoff: float = 1.0,
    ) -> None:
        self.track_id = track_id
        self.state = TrackState.NEW
        self.handedness_stabilizer = HandednessStabilizer(
            window_size=window_size,
            switch_threshold=switch_threshold,
        )
        self.landmark_filter = HandLandmarkFilter(
            min_cutoff=min_cutoff,
            beta=beta,
            d_cutoff=d_cutoff,
        )

        self.last_seen_timestamp = timestamp
        self.palm_center = initial_candidate.palm_center
        self.hand_center = initial_candidate.hand_center
        self.bounding_box = initial_candidate.bounding_box
        self.velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)

        self.missed_frames = 0
        self.total_detections = 0
        self.last_hand_state: Optional[HandState] = None

    def update(
        self,
        candidate: RawHandCandidate,
        timestamp: float,
        normalizer: LandmarkNormalizer,
    ) -> HandState:
        """
        Update the hand track with a new matched candidate detection.
        """
        # 1. Update temporal handedness on this track's dedicated stabilizer
        stabilized_handedness, stabilized_conf = self.handedness_stabilizer.update(
            candidate.raw_handedness, candidate.raw_confidence
        )

        # 2. Filter landmarks on this track's dedicated One Euro filter
        filtered_landmarks = self.landmark_filter.filter_landmarks(
            candidate.raw_landmarks, timestamp
        )

        # 3. Recompute bounding box, palm center, and hand center from filtered landmarks
        bbox = normalizer._calculate_bounding_box(filtered_landmarks)
        palm_ctr = normalizer._calculate_palm_center(filtered_landmarks)
        hand_ctr = normalizer._calculate_hand_center(filtered_landmarks)

        # 4. Update velocity estimation only after initial confirmation frame
        dt = timestamp - self.last_seen_timestamp
        if self.total_detections > 0 and dt > 0.005:
            vx = max(-3.0, min(3.0, (palm_ctr[0] - self.palm_center[0]) / dt))
            vy = max(-3.0, min(3.0, (palm_ctr[1] - self.palm_center[1]) / dt))
            vz = max(-3.0, min(3.0, (palm_ctr[2] - self.palm_center[2]) / dt))
            # Smooth velocity (EMA)
            self.velocity = (
                0.6 * self.velocity[0] + 0.4 * vx,
                0.6 * self.velocity[1] + 0.4 * vy,
                0.6 * self.velocity[2] + 0.4 * vz,
            )
        else:
            self.velocity = (0.0, 0.0, 0.0)

        # 5. Update track internal states
        self.palm_center = palm_ctr
        self.hand_center = hand_ctr
        self.bounding_box = bbox
        self.last_seen_timestamp = timestamp
        self.missed_frames = 0
        self.total_detections += 1
        self.state = TrackState.ACTIVE

        hand_state = HandState(
            handedness=stabilized_handedness,
            confidence=stabilized_conf,
            landmarks=filtered_landmarks,
            bounding_box=bbox,
            palm_center=palm_ctr,
            hand_center=hand_ctr,
            timestamp=timestamp,
            hand_id=self.track_id,
        )
        self.last_hand_state = hand_state
        return hand_state

    def mark_missed(self, timestamp: float) -> None:
        """Record a missed frame for this track."""
        self.missed_frames += 1
        self.state = TrackState.TEMPORARILY_LOST

    def predict_palm_center(self, timestamp: float) -> Tuple[float, float, float]:
        """Extrapolate palm center position based on current velocity."""
        dt = max(0.0, min(0.1, timestamp - self.last_seen_timestamp))
        return (
            self.palm_center[0] + self.velocity[0] * dt,
            self.palm_center[1] + self.velocity[1] * dt,
            self.palm_center[2] + self.velocity[2] * dt,
        )


class TemporalHandTracker:
    """
    Coordinates multi-hand temporal association, isolated state updates,
    and track lifecycles.

    Parameters
    ----------
    max_lost_time: float
        Maximum seconds a hand track can be unseen before expiring (default: 0.30s).
    max_missed_frames: int
        Maximum consecutive missed frames before expiring (default: 8).
    gating_distance: float
        Maximum normalized 2D distance for candidate-to-track matching (default: 0.38).
    window_size: int
        Handedness voting window size (default: 7).
    switch_threshold: float
        Handedness voting switch ratio (default: 0.65).
    min_cutoff: float
        One Euro filter min cutoff (default: 1.0).
    beta: float
        One Euro filter beta (default: 0.007).
    d_cutoff: float
        One Euro filter d_cutoff (default: 1.0).
    """

    def __init__(
        self,
        max_lost_time: float = 0.30,
        max_missed_frames: int = 8,
        gating_distance: float = 0.38,
        window_size: int = 7,
        switch_threshold: float = 0.65,
        min_cutoff: float = 1.0,
        beta: float = 0.007,
        d_cutoff: float = 1.0,
    ) -> None:
        self._max_lost_time = max_lost_time
        self._max_missed_frames = max_missed_frames
        self._gating_distance = gating_distance
        self._window_size = window_size
        self._switch_threshold = switch_threshold
        self._min_cutoff = min_cutoff
        self._beta = beta
        self._d_cutoff = d_cutoff

        self._tracks: Dict[int, HandTrack] = {}
        self._next_track_id: int = 0
        self._normalizer = LandmarkNormalizer()

    def reset(self) -> None:
        """Clear all active and historical tracks."""
        self._tracks.clear()
        self._next_track_id = 0
        logger.debug("TemporalHandTracker reset: all tracks cleared.")

    @property
    def active_track_count(self) -> int:
        """Number of active or temporarily lost tracks currently managed."""
        return len(self._tracks)

    def update(
        self,
        candidates: Sequence[RawHandCandidate],
        timestamp: float,
    ) -> List[HandState]:
        """
        Associate raw candidate detections with existing hand tracks, update states,
        and return the active list of HandState objects.
        """
        # 1. Prune expired tracks based on elapsed time or missed frame threshold
        self._prune_expired_tracks(timestamp)

        # 2. Build cost matrix between existing tracks and incoming candidates
        existing_ids = list(self._tracks.keys())
        num_tracks = len(existing_ids)
        num_cands = len(candidates)

        matched_tracks: Dict[int, int] = {}  # track_id -> cand_idx
        matched_cands: set[int] = set()

        if num_tracks > 0 and num_cands > 0:
            # Build cost matrix
            cost_matrix: List[List[float]] = []
            for t_id in existing_ids:
                track = self._tracks[t_id]
                pred_palm = track.predict_palm_center(timestamp)
                row: List[float] = []
                for cand_idx, cand in enumerate(candidates):
                    # Spatial Euclidean distance in normalized (x, y) space
                    dx = pred_palm[0] - cand.palm_center[0]
                    dy = pred_palm[1] - cand.palm_center[1]
                    dist_2d = math.sqrt(dx * dx + dy * dy)

                    if dist_2d > self._gating_distance:
                        row.append(float("inf"))
                    else:
                        cost = dist_2d
                        # Soft secondary penalty if candidate raw handedness conflicts with track's current classification
                        curr_handedness = track.handedness_stabilizer._current_stabilized
                        if (
                            curr_handedness != Handedness.UNKNOWN
                            and cand.raw_handedness != Handedness.UNKNOWN
                            and curr_handedness != cand.raw_handedness
                        ):
                            cost += 0.12  # Mild penalty; does not block match if spatial distance is small
                        row.append(cost)
                cost_matrix.append(row)

            # Global greedy minimum-cost assignment
            pairs: List[Tuple[float, int, int]] = []
            for i, t_id in enumerate(existing_ids):
                for j in range(num_cands):
                    c = cost_matrix[i][j]
                    if c < float("inf"):
                        pairs.append((c, t_id, j))

            pairs.sort(key=lambda x: x[0])
            used_tracks: set[int] = set()

            for cost, t_id, j in pairs:
                if t_id not in used_tracks and j not in matched_cands:
                    matched_tracks[t_id] = j
                    used_tracks.add(t_id)
                    matched_cands.add(j)
                    logger.debug(
                        "TemporalTracker: Matched track_id=%d to candidate %d (cost=%.3f)",
                        t_id, j, cost
                    )

        # 3. Update matched tracks
        active_hand_states: List[HandState] = []
        for t_id, cand_idx in matched_tracks.items():
            track = self._tracks[t_id]
            cand = candidates[cand_idx]
            hand_state = track.update(cand, timestamp, self._normalizer)
            active_hand_states.append(hand_state)

        # 4. Spawn new tracks for unmatched candidates
        for cand_idx, cand in enumerate(candidates):
            if cand_idx not in matched_cands:
                new_track_id = self._next_track_id
                self._next_track_id = (self._next_track_id + 1) % 100000

                new_track = HandTrack(
                    track_id=new_track_id,
                    initial_candidate=cand,
                    timestamp=timestamp,
                    window_size=self._window_size,
                    switch_threshold=self._switch_threshold,
                    min_cutoff=self._min_cutoff,
                    beta=self._beta,
                    d_cutoff=self._d_cutoff,
                )
                hand_state = new_track.update(cand, timestamp, self._normalizer)
                self._tracks[new_track_id] = new_track
                active_hand_states.append(hand_state)
                logger.debug(
                    "TemporalTracker: Created new track_id=%d for candidate %d (handedness=%s, conf=%.2f)",
                    new_track_id, cand_idx, cand.raw_handedness.name, cand.raw_confidence
                )

        # 5. Mark unmatched tracks as missed
        for t_id in existing_ids:
            if t_id not in matched_tracks:
                track = self._tracks[t_id]
                track.mark_missed(timestamp)
                logger.debug(
                    "TemporalTracker: Track %d missed (%d consecutive missed frames)",
                    t_id, track.missed_frames
                )

        # 6. Sort returned hand states deterministically by track_id
        active_hand_states.sort(key=lambda hs: hs.hand_id)
        return active_hand_states

    def _prune_expired_tracks(self, timestamp: float) -> None:
        """Remove tracks that have exceeded max_lost_time or max_missed_frames."""
        expired_ids: List[int] = []
        for t_id, track in self._tracks.items():
            time_lost = timestamp - track.last_seen_timestamp
            if time_lost > self._max_lost_time or track.missed_frames >= self._max_missed_frames:
                expired_ids.append(t_id)

        for t_id in expired_ids:
            del self._tracks[t_id]
            logger.debug("TemporalTracker: Expired track_id=%d and cleaned up state.", t_id)
