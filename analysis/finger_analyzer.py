"""
gesturedrive.analysis.finger_analyzer
======================================
Robust, real-time finger state analyzer using 3D joint angles, dedicated thumb
geometry, state hysteresis, temporal majority voting, and multi-factor confidence scoring.

Design Features
---------------
1. 3D Joint-Angle Geometry:
   Rotation- and scale-invariant 3D vector angle calculations for Index, Middle, Ring, Pinky.
2. Dedicated Thumb Analyzer:
   Custom anatomical angle and relative palm geometry for Thumb (works for both LEFT and RIGHT hands).
3. Hysteresis:
   Dual-threshold boundaries with state persistence margins to prevent state oscillation.
4. Temporal Stabilization:
   Rolling history deque with weighted majority voting over 5-8 frames.
5. Multi-Factor Confidence:
   Integrates geometric clearance, landmark anatomical stability, and temporal agreement into a [0.10, 1.00] score.
6. Configurable:
   All thresholds sourced from injected AnalysisConfig.
"""

from __future__ import annotations

import math
from collections import deque
from typing import Dict, List, Optional, Sequence, Tuple

from config.schema import AnalysisConfig
from analysis.finger_state import (
    FingerName,
    FingerPosition,
    FingerState,
    HandAnalysis,
)
from tracking.hand_state import HandState, Landmark


class FingerAnalyzer:
    """
    Analyzes 3D landmark geometry from a ``HandState`` to evaluate the flexion
    position of all five fingers independently with temporal stabilization.

    Parameters
    ----------
    config:
        Optional ``AnalysisConfig`` section. If ``None``, default config is used.
    """

    def __init__(self, config: Optional[AnalysisConfig] = None) -> None:
        self._config = config or AnalysisConfig()
        # History of candidate positions per (hand_id, finger_name)
        self._history: Dict[Tuple[int, FingerName], deque[FingerPosition]] = {}
        # Last reported position per (hand_id, finger_name) for hysteresis
        self._prev_state: Dict[Tuple[int, FingerName], FingerPosition] = {}

    def reset(self) -> None:
        """Clear temporal history and state cache."""
        self._history.clear()
        self._prev_state.clear()

    def cleanup_expired_hands(self, active_hand_ids: Sequence[int]) -> None:
        """
        Remove cached finger history and previous states for hand IDs that are no longer active.
        """
        active_set = set(active_hand_ids)
        history_keys_to_remove = [k for k in self._history if k[0] not in active_set]
        for k in history_keys_to_remove:
            del self._history[k]

        prev_keys_to_remove = [k for k in self._prev_state if k[0] not in active_set]
        for k in prev_keys_to_remove:
            del self._prev_state[k]

    def cleanup_hand(self, hand_id: int) -> None:
        """
        Remove cached finger history and previous states for a specific expired hand ID.
        """
        history_keys_to_remove = [k for k in self._history if k[0] == hand_id]
        for k in history_keys_to_remove:
            del self._history[k]

        prev_keys_to_remove = [k for k in self._prev_state if k[0] == hand_id]
        for k in prev_keys_to_remove:
            del self._prev_state[k]

    def analyze(self, hand_state: HandState) -> HandAnalysis:
        """
        Analyze a ``HandState`` and produce a temporally stabilized ``HandAnalysis``.

        Parameters
        ----------
        hand_state:
            Normalized 21-landmark hand state from the tracking module.

        Returns
        -------
        HandAnalysis
            Aggregated finger states for Thumb, Index, Middle, Ring, and Pinky.
        """
        thumb = self._analyze_thumb(hand_state)
        index = self._analyze_index(hand_state)
        middle = self._analyze_middle(hand_state)
        ring = self._analyze_ring(hand_state)
        pinky = self._analyze_pinky(hand_state)

        return HandAnalysis(
            hand_state=hand_state,
            thumb=thumb,
            index=index,
            middle=middle,
            ring=ring,
            pinky=pinky,
            timestamp=hand_state.timestamp,
        )

    # ── Dedicated Per-Finger Analyzers ─────────────────────────────────────────

    def _analyze_thumb(self, hand_state: HandState) -> FingerState:
        """
        Multi-signal Thumb analyzer combining:
        1. 3D joint angles (CMC 1, MCP 2, IP 3, TIP 4).
        2. 3D relative distances to Palm Center, Index MCP (5), Pinky MCP (17), and Wrist (0).
        3. Palm plane normal vector and 3D plane clearance.
        4. Fist context & landmark occlusion detection.
        5. Temporal persistence when landmarks are occluded/hidden.
        6. Viewpoint invariance (works for palm-facing, back of hand, rotation, and tilt).
        """
        if len(hand_state.landmarks) < 21:
            return FingerState(
                name=FingerName.THUMB,
                position=FingerPosition.UNKNOWN,
                confidence=0.0,
            )

        lms = hand_state.landmarks
        wrist      = lms[0]
        cmc        = lms[1]
        mcp        = lms[2]
        ip         = lms[3]
        tip        = lms[4]
        index_mcp  = lms[5]
        index_tip  = lms[8]
        middle_mcp = lms[9]
        pinky_mcp  = lms[17]

        key = (getattr(hand_state, "hand_id", 0), FingerName.THUMB)
        prev_pos = self._prev_state.get(key, FingerPosition.UNKNOWN)

        # 1. Palm Center & Reference Scale
        palm_center_x = (wrist.x + index_mcp.x + middle_mcp.x + pinky_mcp.x) / 4.0
        palm_center_y = (wrist.y + index_mcp.y + middle_mcp.y + pinky_mcp.y) / 4.0
        palm_center_z = (wrist.z + index_mcp.z + middle_mcp.z + pinky_mcp.z) / 4.0

        palm_width  = self._distance_3d(index_mcp, pinky_mcp)
        palm_length = self._distance_3d(wrist, middle_mcp)
        scale = max(0.001, (palm_width + palm_length) / 2.0)

        # 2. Key 3D relative distances
        d_tip_palm   = math.sqrt((tip.x - palm_center_x)**2 + (tip.y - palm_center_y)**2 + (tip.z - palm_center_z)**2) / scale
        d_tip_index  = self._distance_3d(tip, index_mcp) / scale
        d_tip_wrist  = self._distance_3d(tip, wrist) / scale
        d_tip_pinky  = self._distance_3d(tip, pinky_mcp) / scale

        # 3. Palm Normal Vector (Cross product of Wrist->IndexMCP and Wrist->PinkyMCP)
        u_x, u_y, u_z = index_mcp.x - wrist.x, index_mcp.y - wrist.y, index_mcp.z - wrist.z
        v_x, v_y, v_z = pinky_mcp.x - wrist.x, pinky_mcp.y - wrist.y, pinky_mcp.z - wrist.z

        nx = u_y * v_z - u_z * v_y
        ny = u_z * v_x - u_x * v_z
        nz = u_x * v_y - u_y * v_x
        n_mag = math.sqrt(nx * nx + ny * ny + nz * nz)
        if n_mag > 0:
            nx, ny, nz = nx / n_mag, ny / n_mag, nz / n_mag
        else:
            nx, ny, nz = 0.0, 0.0, 1.0

        # Distance of Thumb TIP perpendicular to Palm Plane
        plane_dist = abs((tip.x - wrist.x) * nx + (tip.y - wrist.y) * ny + (tip.z - wrist.z) * nz) / scale

        # 4. 3D Joint Angles
        ip_angle  = self._angle_3d(mcp, ip, tip)
        mcp_angle = self._angle_3d(cmc, mcp, ip)

        # 5. Nearby Finger Context (are index and middle fingers curled in a fist?)
        middle_tip = lms[12]
        index_curl_dist = self._distance_3d(index_tip, index_mcp) / scale
        middle_curl_dist = self._distance_3d(middle_tip, middle_mcp) / scale
        is_fist_context = (index_curl_dist < 0.70 and middle_curl_dist < 0.70)

        # 6. Thumb Spatial Projections
        thumb_elevation = (index_mcp.y - tip.y) / scale
        thumb_upward_vec = (mcp.y - tip.y) / scale
        thumb_depression = (tip.y - mcp.y) / scale
        thumb_span = self._distance_3d(mcp, tip) / scale
        thumb_len = self._distance_3d(cmc, mcp) + self._distance_3d(mcp, ip) + self._distance_3d(ip, tip)
        is_occluded = (thumb_len < scale * 0.40) or (d_tip_index < 0.22)

        is_thumbs_up = (thumb_elevation >= 0.28 and thumb_upward_vec >= 0.22 and thumb_span >= 0.30)
        is_thumbs_down = (thumb_depression >= 0.08 and thumb_span >= 0.28 and ((tip.y - index_mcp.y) / scale) >= 0.08)

        # 7. Multi-Signal Fusion Metric Calculation
        s_palm  = min(1.0, max(0.0, d_tip_palm / 0.65))
        s_index = min(1.0, max(0.0, d_tip_index / 0.55))
        s_plane = min(1.0, max(0.0, plane_dist / 0.35))
        s_angle = min(1.0, max(0.0, ip_angle / 160.0))

        fusion_score = 0.35 * s_palm + 0.35 * s_index + 0.15 * s_plane + 0.15 * s_angle

        # 8. Apply Fist Fold or Extension Context
        if is_fist_context:
            if is_thumbs_up:
                fusion_score = max(fusion_score, 0.85)
            elif is_thumbs_down:
                fusion_score = max(fusion_score, 0.85)
            else:
                # Naturally folded across curled fingers or resting against palm
                fusion_score = min(fusion_score * 0.25, 0.20)
        else:
            if is_occluded or d_tip_index < 0.25:
                fusion_score *= 0.40

        if d_tip_pinky < 0.60 and not (is_thumbs_up or is_thumbs_down):
            fold_penalty = (0.60 - d_tip_pinky) * 0.70
            fusion_score = max(0.0, fusion_score - fold_penalty)

        # Map fusion_score (0.0 .. 1.0) into effective angle (90.0 .. 180.0 deg) for hysteresis
        thumb_angle = 90.0 + fusion_score * 90.0

        ext_thresh  = self._config.thumb_extended_angle
        curl_thresh = self._config.thumb_curled_angle
        margin      = self._config.finger_hysteresis_margin

        # Hysteresis Classification
        candidate_pos = self._classify_with_hysteresis(
            angle=thumb_angle,
            ext_thresh=ext_thresh,
            curl_thresh=curl_thresh,
            margin=margin,
            prev_pos=prev_pos,
        )

        # If occluded & in fist context without explicit extension, default candidate to CURLED
        if is_occluded and is_fist_context and not (is_thumbs_up or is_thumbs_down):
            candidate_pos = FingerPosition.CURLED

        # Temporal Majority Voting
        final_pos, temporal_conf = self._apply_temporal_smoothing(key, candidate_pos)
        self._prev_state[key] = final_pos

        # Multi-factor Confidence Estimation
        geom_conf = self._calculate_geometric_confidence(
            angle=thumb_angle,
            ext_thresh=ext_thresh,
            curl_thresh=curl_thresh,
            position=final_pos,
        )

        signal_spread = abs(s_palm - s_index) + abs(s_index - s_plane)
        agreement_conf = max(0.60, 1.00 - signal_spread * 0.25)
        if is_occluded:
            agreement_conf *= 0.85

        final_conf = round(
            max(0.10, min(1.00, 0.40 * geom_conf + 0.30 * agreement_conf + 0.30 * temporal_conf)),
            2,
        )

        return FingerState(
            name=FingerName.THUMB,
            position=final_pos,
            confidence=final_conf,
        )

    def _analyze_index(self, hand_state: HandState) -> FingerState:
        """Analyze Index finger using 3D joint angles (MCP 5, PIP 6, DIP 7, TIP 8)."""
        return self._analyze_finger(
            hand_state=hand_state,
            finger_name=FingerName.INDEX,
            mcp_idx=5, pip_idx=6, dip_idx=7, tip_idx=8,
        )

    def _analyze_middle(self, hand_state: HandState) -> FingerState:
        """Analyze Middle finger using 3D joint angles (MCP 9, PIP 10, DIP 11, TIP 12)."""
        return self._analyze_finger(
            hand_state=hand_state,
            finger_name=FingerName.MIDDLE,
            mcp_idx=9, pip_idx=10, dip_idx=11, tip_idx=12,
        )

    def _analyze_ring(self, hand_state: HandState) -> FingerState:
        """Analyze Ring finger using 3D joint angles (MCP 13, PIP 14, DIP 15, TIP 16)."""
        return self._analyze_finger(
            hand_state=hand_state,
            finger_name=FingerName.RING,
            mcp_idx=13, pip_idx=14, dip_idx=15, tip_idx=16,
        )

    def _analyze_pinky(self, hand_state: HandState) -> FingerState:
        """Analyze Pinky finger using 3D joint angles (MCP 17, PIP 18, DIP 19, TIP 20)."""
        return self._analyze_finger(
            hand_state=hand_state,
            finger_name=FingerName.PINKY,
            mcp_idx=17, pip_idx=18, dip_idx=19, tip_idx=20,
        )

    # ── Core Joint Angle & Hysteresis Pipeline ────────────────────────────────

    def _analyze_finger(
        self,
        hand_state: HandState,
        finger_name: FingerName,
        mcp_idx: int,
        pip_idx: int,
        dip_idx: int,
        tip_idx: int,
    ) -> FingerState:
        """
        Compute 3D joint angles at PIP and DIP to evaluate finger state
        with hysteresis, temporal majority voting, and confidence estimation.
        """
        if len(hand_state.landmarks) < 21:
            return FingerState(
                name=finger_name,
                position=FingerPosition.UNKNOWN,
                confidence=0.0,
            )

        lms = hand_state.landmarks
        mcp = lms[mcp_idx]
        pip = lms[pip_idx]
        dip = lms[dip_idx]
        tip = lms[tip_idx]

        # 3D Joint Angles at PIP and DIP
        pip_angle = self._angle_3d(mcp, pip, dip)
        dip_angle = self._angle_3d(pip, dip, tip)

        # Weighted bend angle
        finger_angle = 0.55 * pip_angle + 0.45 * dip_angle

        ext_thresh  = self._config.finger_extended_angle
        curl_thresh = self._config.finger_curled_angle
        margin      = self._config.finger_hysteresis_margin

        key = (getattr(hand_state, "hand_id", 0), finger_name)
        prev_pos = self._prev_state.get(key, FingerPosition.UNKNOWN)

        # Apply Hysteresis
        candidate_pos = self._classify_with_hysteresis(
            angle=finger_angle,
            ext_thresh=ext_thresh,
            curl_thresh=curl_thresh,
            margin=margin,
            prev_pos=prev_pos,
        )

        # Temporal Majority Voting
        final_pos, temporal_conf = self._apply_temporal_smoothing(key, candidate_pos)
        self._prev_state[key] = final_pos

        # Geometric confidence
        geom_conf = self._calculate_geometric_confidence(
            angle=finger_angle,
            ext_thresh=ext_thresh,
            curl_thresh=curl_thresh,
            position=final_pos,
        )

        # Landmark structural stability confidence
        seg1 = self._distance_3d(mcp, pip)
        seg2 = self._distance_3d(pip, dip)
        stability_conf = 0.95 if (seg1 > 0 and seg2 > 0 and 0.6 <= (seg1 / seg2) <= 2.2) else 0.65

        final_conf = round(
            max(0.10, min(1.00, 0.40 * geom_conf + 0.30 * stability_conf + 0.30 * temporal_conf)),
            2,
        )

        return FingerState(
            name=finger_name,
            position=final_pos,
            confidence=final_conf,
        )

    # ── Classification & Hysteresis ───────────────────────────────────────────

    @staticmethod
    def _classify_with_hysteresis(
        angle: float,
        ext_thresh: float,
        curl_thresh: float,
        margin: float,
        prev_pos: FingerPosition,
    ) -> FingerPosition:
        """
        Classify finger angle into FingerPosition using state hysteresis margins.
        """
        if prev_pos == FingerPosition.EXTENDED:
            if angle >= (ext_thresh - margin):
                return FingerPosition.EXTENDED
            elif angle <= curl_thresh:
                return FingerPosition.CURLED
            else:
                return FingerPosition.PARTIALLY_BENT

        elif prev_pos == FingerPosition.CURLED:
            if angle <= (curl_thresh + margin):
                return FingerPosition.CURLED
            elif angle >= ext_thresh:
                return FingerPosition.EXTENDED
            else:
                return FingerPosition.PARTIALLY_BENT

        else:  # PARTIALLY_BENT or UNKNOWN
            if angle >= ext_thresh:
                return FingerPosition.EXTENDED
            elif angle <= curl_thresh:
                return FingerPosition.CURLED
            else:
                return FingerPosition.PARTIALLY_BENT

    # ── Temporal Majority Voting ───────────────────────────────────────────────

    def _apply_temporal_smoothing(
        self,
        key: Tuple[int, FingerName],
        candidate_pos: FingerPosition,
    ) -> Tuple[FingerPosition, float]:
        """
        Maintain rolling history and apply weighted majority voting to stabilize states.
        """
        history_size = max(1, self._config.history_size)
        if key not in self._history:
            self._history[key] = deque(maxlen=history_size)

        buf = self._history[key]
        buf.append(candidate_pos)

        # Exponentially higher weights for recent frames
        n = len(buf)
        weights = [i + 1 for i in range(n)]
        total_weight = float(sum(weights))

        vote_counts: Dict[FingerPosition, float] = {}
        for pos, w in zip(buf, weights):
            vote_counts[pos] = vote_counts.get(pos, 0.0) + float(w)

        winning_pos = max(vote_counts.keys(), key=lambda p: vote_counts[p])
        winning_weight = vote_counts[winning_pos]

        temporal_agreement = winning_weight / total_weight if total_weight > 0 else 1.0
        return winning_pos, temporal_agreement

    # ── Geometric Confidence Helper ───────────────────────────────────────────

    @staticmethod
    def _calculate_geometric_confidence(
        angle: float,
        ext_thresh: float,
        curl_thresh: float,
        position: FingerPosition,
    ) -> float:
        """Calculate confidence based on joint angle clearance from decision boundaries."""
        if position == FingerPosition.EXTENDED:
            diff = max(0.0, angle - ext_thresh)
            return min(1.0, 0.75 + 0.25 * min(1.0, diff / 25.0))
        elif position == FingerPosition.CURLED:
            diff = max(0.0, curl_thresh - angle)
            return min(1.0, 0.75 + 0.25 * min(1.0, diff / 25.0))
        else:  # PARTIALLY_BENT
            mid = (ext_thresh + curl_thresh) / 2.0
            range_h = (ext_thresh - curl_thresh) / 2.0
            diff = abs(angle - mid)
            if range_h > 0:
                norm_dist = max(0.0, 1.0 - (diff / range_h))
                return 0.70 + 0.25 * norm_dist
            return 0.80

    # ── Geometry Math Primitives ──────────────────────────────────────────────

    @staticmethod
    def _angle_3d(p1: Landmark, p2: Landmark, p3: Landmark) -> float:
        """
        Calculate 3D Euclidean angle at vertex p2 between vectors (p1-p2) and (p3-p2) in degrees.
        """
        v1_x, v1_y, v1_z = p1.x - p2.x, p1.y - p2.y, p1.z - p2.z
        v2_x, v2_y, v2_z = p3.x - p2.x, p3.y - p2.y, p3.z - p2.z

        mag1 = math.sqrt(v1_x * v1_x + v1_y * v1_y + v1_z * v1_z)
        mag2 = math.sqrt(v2_x * v2_x + v2_y * v2_y + v2_z * v2_z)

        if mag1 == 0.0 or mag2 == 0.0:
            return 180.0

        dot = v1_x * v2_x + v1_y * v2_y + v1_z * v2_z
        cos_angle = max(-1.0, min(1.0, dot / (mag1 * mag2)))
        return math.degrees(math.acos(cos_angle))

    @staticmethod
    def _distance_3d(p1: Landmark, p2: Landmark) -> float:
        """Calculate 3D Euclidean distance between two Landmark points."""
        dx = p1.x - p2.x
        dy = p1.y - p2.y
        dz = p1.z - p2.z
        return math.sqrt(dx * dx + dy * dy + dz * dz)
