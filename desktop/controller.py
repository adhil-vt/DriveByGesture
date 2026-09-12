"""
gesturedrive.desktop.controller
================================
DesktopController: translates hand positions and recognized gestures
into desktop cursor movements and system control actions.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional, Sequence, Tuple

from analysis.finger_state import FingerPosition, HandAnalysis
from desktop.actions import DesktopAction
from desktop.bindings import GestureBindingManager
from desktop.enums import DesktopActionType, DesktopState
from desktop.executor import IOSDesktopExecutor, get_desktop_executor
from gestures.builtins.utils import distance_3d
from gestures.gesture_result import GestureResult

logger = logging.getLogger(__name__)


class DesktopController:
    """
    Main controller for Desktop Gesture Mode with Finger Articulation Lock (zero click/pinch drift),
    Decoupled Mouse Action State Machine, drag target anchoring, and release hysteresis.

    Parameters
    ----------
    executor: Optional[IOSDesktopExecutor]
        Hardware execution engine (defaults to Windows/Null native executor).
    binding_manager: Optional[GestureBindingManager]
        Resolver for gesture-to-action mappings.
    """

    def __init__(
        self,
        executor: Optional[IOSDesktopExecutor] = None,
        binding_manager: Optional[GestureBindingManager] = None,
    ) -> None:
        self.executor = executor or get_desktop_executor()
        self.binding_manager = binding_manager or GestureBindingManager()

        # Tunable Config Parameters
        self.cursor_sensitivity: float = 1.75
        self.cursor_smoothing: float = 0.25
        self.cursor_deadzone: float = 0.05
        self.invert_x: bool = False
        self.invert_y: bool = False
        self.cursor_enabled: bool = True
        self.click_delay: float = 0.2
        self.scroll_speed: float = 1.0
        self.gesture_cooldown: float = 0.3
        self.repeat_delay: float = 0.5
        self.cursor_acceleration: bool = True
        self.workspace_w_pct: float = 0.80
        self.workspace_h_pct: float = 0.80
        self.show_workspace_overlay: bool = True
        self.custom_shortcut: str = "ctrl+tab"
        self.enabled_actions: Dict[str, bool] = {}

        # Internal Controller State Machine
        self._screen_w, self._screen_h = self.executor.get_screen_size()
        self._curr_x: float = float(self._screen_w // 2)
        self._curr_y: float = float(self._screen_h // 2)
        self._desktop_state: DesktopState = DesktopState.IDLE
        self._is_dragging: bool = False
        self._drag_release_counter: int = 0
        self._drag_ref_mcp_pos: Optional[Tuple[float, float]] = None
        self._drag_start_cursor_pos: Optional[Tuple[float, float]] = None
        self._last_action_time: float = 0.0
        self._last_action_type: DesktopActionType = DesktopActionType.NONE
        self._active_action_name: str = "Idle"
        self._control_active: bool = False

        # Drag Transition & Anchor Stabilization (Phase 14.5)
        self._last_point_cursor_pos: Tuple[float, float] = (self._curr_x, self._curr_y)
        self._last_point_time: float = 0.0
        self._drag_pending: bool = False
        self._drag_pending_start_time: float = 0.0
        self._cursor_offset_x: float = 0.0
        self._cursor_offset_y: float = 0.0
        self._reanchor_needed: bool = False

    # ── State Accessors ───────────────────────────────────────────────────────

    @property
    def active_action_name(self) -> str:
        return self._active_action_name

    @property
    def is_control_active(self) -> bool:
        return self._control_active

    @property
    def cursor_pos(self) -> Tuple[int, int]:
        return (int(self._curr_x), int(self._curr_y))

    def reset(self) -> None:
        """Safely release any active drag and reset all internal controller state."""
        if self._is_dragging:
            self.executor.mouse_up()
        self._is_dragging = False
        self._drag_release_counter = 0
        self._drag_pending = False
        self._drag_pending_start_time = 0.0
        self._drag_ref_mcp_pos = None
        self._drag_start_cursor_pos = None
        self._reanchor_needed = False
        self._cursor_offset_x = 0.0
        self._cursor_offset_y = 0.0
        self._desktop_state = DesktopState.IDLE
        self._active_action_name = "Idle"
        self._control_active = False

    def apply_config(self, config_dict: Dict[str, Any]) -> None:
        """Apply desktop settings dictionary live."""
        if not config_dict:
            return
        if hasattr(config_dict, "to_dict"):
            config_dict = config_dict.to_dict()
        self.cursor_sensitivity     = float(config_dict.get("cursor_sensitivity", 1.75))
        self.cursor_smoothing       = float(config_dict.get("cursor_smoothing", 0.25))
        self.cursor_deadzone        = float(config_dict.get("cursor_deadzone", 0.05))
        self.invert_x               = bool(config_dict.get("invert_x", False))
        self.invert_y               = bool(config_dict.get("invert_y", False))
        self.cursor_enabled         = bool(config_dict.get("cursor_enabled", True))
        self.click_delay            = float(config_dict.get("click_delay", 0.2))
        self.scroll_speed           = float(config_dict.get("scroll_speed", 1.0))
        self.gesture_cooldown       = float(config_dict.get("gesture_cooldown", 0.3))
        self.repeat_delay           = float(config_dict.get("repeat_delay", 0.5))
        self.cursor_acceleration    = bool(config_dict.get("cursor_acceleration", True))
        self.workspace_w_pct        = float(config_dict.get("workspace_w_pct", 0.80))
        self.workspace_h_pct        = float(config_dict.get("workspace_h_pct", 0.80))
        self.show_workspace_overlay = bool(config_dict.get("show_workspace_overlay", True))
        self.custom_shortcut        = str(config_dict.get("custom_shortcut", "ctrl+tab"))
        if "enabled_actions" in config_dict and isinstance(config_dict["enabled_actions"], dict):
            self.enabled_actions = config_dict["enabled_actions"]

        if "bindings" in config_dict and isinstance(config_dict["bindings"], dict):
            self.binding_manager.set_bindings_dict(config_dict["bindings"])

        logger.info("DesktopController: config updated live.")

    # ── Frame Processing Loop ─────────────────────────────────────────────────

    def process(
        self,
        hands: Sequence[Any],
        hand_analyses: Optional[Sequence[HandAnalysis]],
        gesture_results: Sequence[GestureResult],
    ) -> Dict[str, Any]:
        """
        Process current frame hand landmarks and recognized gestures into desktop actions.
        Drives state machine transitions with finger articulation lock and release hysteresis.
        """
        now = time.monotonic()
        self._control_active = bool(hands)
        self._active_action_name = "Idle"

        if not hands:
            if self._is_dragging:
                self.executor.mouse_up()
                self._is_dragging = False
                self._drag_release_counter = 0
                self._desktop_state = DesktopState.IDLE
            self._drag_pending = False
            self._drag_pending_start_time = 0.0
            return self._build_telemetry("None", DesktopActionType.NONE)

        # 1. Resolve Gesture to Desktop Action
        detected_gesture = "None"
        target_action_type = DesktopActionType.NONE

        for g_res in gesture_results:
            if not g_res or not g_res.detected or g_res.gesture_name == "Unknown":
                continue
            detected_gesture = g_res.gesture_name
            resolved = self.binding_manager.resolve_action(detected_gesture)
            if resolved != DesktopActionType.NONE:
                if self.enabled_actions and not self.enabled_actions.get(resolved.name, True):
                    continue
                target_action_type = resolved
                break

        hand0 = hands[0]
        lms = getattr(hand0, "landmarks", None)
        ha0 = hand_analyses[0] if hand_analyses and len(hand_analyses) > 0 else None

        norm_pinch_dist = 1.0
        if lms and len(lms) >= 21:
            d_ti = distance_3d(lms[4], lms[8])
            scale = (distance_3d(lms[5], lms[17]) + distance_3d(lms[0], lms[9])) / 2.0
            if scale > 0:
                norm_pinch_dist = d_ti / scale

        # Treat Pinch gesture as DRAG if bound to DRAG or LEFT_CLICK
        is_drag_gesture = (
            target_action_type == DesktopActionType.DRAG
            or (detected_gesture == "Pinch" and target_action_type in (DesktopActionType.LEFT_CLICK, DesktopActionType.DRAG))
            or (norm_pinch_dist <= 0.38)
        )

        is_pinch_approach = (norm_pinch_dist <= 0.55)

        # Point / Interaction Tracking Context
        is_pointing = (
            detected_gesture in ("Point", "Open Palm")
            or (ha0 is not None and ha0.index.position == FingerPosition.EXTENDED and ha0.middle.position in (FingerPosition.CURLED, FingerPosition.PARTIALLY_BENT))
        )

        if is_pointing and not self._is_dragging:
            self._last_point_cursor_pos = (self._curr_x, self._curr_y)
            self._last_point_time = now
            self._drag_pending = False
            self._drag_pending_start_time = 0.0

        # Check for finger-folding transition from Point towards Drag
        is_folding_to_drag = False
        if not self._is_dragging and not is_drag_gesture and (now - self._last_point_time < 0.40):
            if ha0 is not None:
                is_folding_to_drag = (
                    ha0.index.position in (FingerPosition.PARTIALLY_BENT, FingerPosition.CURLED)
                    and ha0.middle.position in (FingerPosition.CURLED, FingerPosition.PARTIALLY_BENT)
                )
            elif lms and len(lms) >= 21:
                scale = (distance_3d(lms[5], lms[17]) + distance_3d(lms[0], lms[9])) / 2.0
                if scale > 0:
                    idx_curl = distance_3d(lms[8], lms[5]) / scale
                    mid_curl = distance_3d(lms[12], lms[9]) / scale
                    is_folding_to_drag = (idx_curl < 0.70 and mid_curl < 0.70)

        if is_folding_to_drag:
            self._drag_pending = True
            if self._drag_pending_start_time == 0.0:
                self._drag_pending_start_time = now
            if now - self._drag_pending_start_time > 0.45:
                self._drag_pending = False
        elif not is_drag_gesture and (detected_gesture in ("Open Palm", "Peace") or (ha0 is not None and ha0.middle.position == FingerPosition.EXTENDED)):
            self._drag_pending = False
            self._drag_pending_start_time = 0.0

        # 2. State Machine Transition & Decoupled Action Processing
        if is_drag_gesture and lms and len(lms) >= 21:
            self._drag_pending = False
            self._drag_pending_start_time = 0.0
            cur_mcp_x = (1.0 - lms[5].x) if not self.invert_x else lms[5].x
            cur_mcp_y = lms[5].y if not self.invert_y else (1.0 - lms[5].y)

            if not self._is_dragging:
                # DRAG_START Transition: Freeze cursor coordinates at stable Point target (Zero Jump Anchor Lock!)
                self._desktop_state = DesktopState.DRAG_START
                self._is_dragging = True
                self._drag_release_counter = 0
                anchor_x, anchor_y = self._last_point_cursor_pos if self._last_point_time > 0 else (self._curr_x, self._curr_y)
                self._curr_x = anchor_x
                self._curr_y = anchor_y
                self._drag_start_cursor_pos = (anchor_x, anchor_y)
                self._drag_ref_mcp_pos = (cur_mcp_x, cur_mcp_y)
                self.executor.set_cursor_pos(int(self._curr_x), int(self._curr_y))
                self.executor.mouse_down()
                self._active_action_name = "Drag (Locked Target)"
            else:
                # DRAGGING State: Smooth relative tracking of Index MCP (Landmark 5) from drag start anchor
                self._desktop_state = DesktopState.DRAGGING
                self._drag_release_counter = 0
                if self._drag_ref_mcp_pos and self._drag_start_cursor_pos:
                    dx = (cur_mcp_x - self._drag_ref_mcp_pos[0]) * self._screen_w * self.cursor_sensitivity
                    dy = (cur_mcp_y - self._drag_ref_mcp_pos[1]) * self._screen_h * self.cursor_sensitivity
                    self._curr_x = max(0.0, min(float(self._screen_w - 1), self._drag_start_cursor_pos[0] + dx))
                    self._curr_y = max(0.0, min(float(self._screen_h - 1), self._drag_start_cursor_pos[1] + dy))
                    self.executor.set_cursor_pos(int(self._curr_x), int(self._curr_y))
                    self._active_action_name = "Dragging"
        else:
            # Non-drag frames: Check 3-frame release guard if dragging was active
            if self._is_dragging:
                self._drag_release_counter += 1
                if self._drag_release_counter < 3:
                    # Maintain dragging state during transient landmark noise
                    self._active_action_name = "Dragging (Stabilizing)"
                else:
                    # DRAG_END Transition: 3 consecutive release frames reached -> mouse_up()
                    self._desktop_state = DesktopState.DRAG_END
                    self.executor.mouse_up()
                    self._is_dragging = False
                    self._drag_release_counter = 0
                    self._drag_ref_mcp_pos = None
                    self._drag_start_cursor_pos = None
                    self._last_point_cursor_pos = (self._curr_x, self._curr_y)
                    self._reanchor_needed = True
                    self._active_action_name = "Idle"
            else:
                if self._drag_pending:
                    # DRAG_PENDING: User folding fingers -> Freeze cursor at stable target, do not drift with index tip!
                    self._desktop_state = DesktopState.DRAG_PENDING
                    self._active_action_name = "Drag (Pending Anchor)"
                    if self._last_point_cursor_pos:
                        self._curr_x, self._curr_y = self._last_point_cursor_pos
                    self.executor.set_cursor_pos(int(self._curr_x), int(self._curr_y))
                elif is_pinch_approach:
                    # ARTICULATION_LOCK: User flexing finger to click/pinch -> Freeze cursor coordinates at target!
                    self._desktop_state = DesktopState.ARTICULATION_LOCK
                    self._active_action_name = "Lock (Target Fixed)"
                    self.executor.set_cursor_pos(int(self._curr_x), int(self._curr_y))
                else:
                    self._desktop_state = DesktopState.MOVING if lms else DesktopState.IDLE

                    # Normal Cursor Movement with Active Workspace Mapping (Comfortable screen edge reach!)
                    if self.cursor_enabled and lms and len(lms) >= 21:
                        index_tip = lms[8]  # Index finger tip
                        raw_norm_x = (1.0 - index_tip.x) if not self.invert_x else index_tip.x
                        raw_norm_y = index_tip.y if not self.invert_y else (1.0 - index_tip.y)

                        # Active interaction workspace mapping
                        ws_w = max(0.50, min(1.0, self.workspace_w_pct))
                        ws_h = max(0.50, min(1.0, self.workspace_h_pct))
                        margin_x = (1.0 - ws_w) / 2.0
                        margin_y = (1.0 - ws_h) / 2.0

                        mapped_norm_x = max(0.0, min(1.0, (raw_norm_x - margin_x) / ws_w))
                        mapped_norm_y = max(0.0, min(1.0, (raw_norm_y - margin_y) / ws_h))

                        raw_target_x = mapped_norm_x * self._screen_w
                        raw_target_y = mapped_norm_y * self._screen_h

                        if self._reanchor_needed:
                            self._reanchor_needed = False
                            self._cursor_offset_x = self._curr_x - raw_target_x
                            self._cursor_offset_y = self._curr_y - raw_target_y

                        target_x = raw_target_x + self._cursor_offset_x
                        target_y = raw_target_y + self._cursor_offset_y

                        # Boundary protection: Adjust offset if target hits boundaries so cursor can reach all edges
                        if target_x < 0:
                            self._cursor_offset_x += (0.0 - target_x)
                            target_x = 0.0
                        elif target_x > self._screen_w - 1:
                            self._cursor_offset_x -= (target_x - (self._screen_w - 1))
                            target_x = float(self._screen_w - 1)

                        if target_y < 0:
                            self._cursor_offset_y += (0.0 - target_y)
                            target_y = 0.0
                        elif target_y > self._screen_h - 1:
                            self._cursor_offset_y -= (target_y - (self._screen_h - 1))
                            target_y = float(self._screen_h - 1)

                        if self.cursor_acceleration:
                            dx = target_x - self._curr_x
                            dy = target_y - self._curr_y
                            dist = (dx * dx + dy * dy) ** 0.5
                            accel_factor = min(2.5, max(1.0, dist / 40.0))
                            target_x = self._curr_x + dx * accel_factor * self.cursor_sensitivity
                            target_y = self._curr_y + dy * accel_factor * self.cursor_sensitivity

                        alpha = max(0.05, min(1.0, self.cursor_smoothing))
                        self._curr_x = self._curr_x * (1.0 - alpha) + target_x * alpha
                        self._curr_y = self._curr_y * (1.0 - alpha) + target_y * alpha

                        self._curr_x = max(0.0, min(float(self._screen_w - 1), self._curr_x))
                        self._curr_y = max(0.0, min(float(self._screen_h - 1), self._curr_y))
                        self.executor.set_cursor_pos(int(self._curr_x), int(self._curr_y))
                        self._last_point_cursor_pos = (self._curr_x, self._curr_y)

                # Execute non-drag action
                if target_action_type != DesktopActionType.NONE and target_action_type != DesktopActionType.DRAG:
                    self._execute_action(target_action_type, now)

        return self._build_telemetry(detected_gesture, target_action_type)

    def _execute_action(self, action_type: DesktopActionType, now: float) -> None:
        """Execute a desktop hardware action with gesture cooldown and repeat rate limiting."""
        elapsed = now - self._last_action_time

        if action_type == DesktopActionType.NONE:
            return

        self._active_action_name = action_type.name.replace("_", " ").title()

        # Cooldown / Debounce checks
        if action_type in (DesktopActionType.LEFT_CLICK, DesktopActionType.RIGHT_CLICK, DesktopActionType.DOUBLE_CLICK):
            if elapsed < self.click_delay:
                return
            self._last_action_time = now

            if action_type == DesktopActionType.LEFT_CLICK:
                self.executor.left_click()
            elif action_type == DesktopActionType.RIGHT_CLICK:
                self.executor.right_click()
            elif action_type == DesktopActionType.DOUBLE_CLICK:
                self.executor.double_click()

        elif action_type in (DesktopActionType.SCROLL_UP, DesktopActionType.SCROLL_DOWN):
            if elapsed < (self.repeat_delay / max(1.0, self.scroll_speed)):
                return
            self._last_action_time = now
            delta = 1 if action_type == DesktopActionType.SCROLL_UP else -1
            self.executor.scroll(delta)

        elif action_type in (DesktopActionType.VOLUME_UP, DesktopActionType.VOLUME_DOWN, DesktopActionType.MUTE):
            if elapsed < self.repeat_delay:
                return
            self._last_action_time = now
            if action_type == DesktopActionType.VOLUME_UP:
                self.executor.volume_up()
            elif action_type == DesktopActionType.VOLUME_DOWN:
                self.executor.volume_down()
            elif action_type == DesktopActionType.MUTE:
                self.executor.mute()

        elif action_type in (DesktopActionType.PLAY_PAUSE, DesktopActionType.NEXT_TRACK, DesktopActionType.PREV_TRACK):
            if elapsed < self.gesture_cooldown:
                return
            self._last_action_time = now
            if action_type == DesktopActionType.PLAY_PAUSE:
                self.executor.play_pause()
            elif action_type == DesktopActionType.NEXT_TRACK:
                self.executor.next_track()
            elif action_type == DesktopActionType.PREV_TRACK:
                self.executor.prev_track()

        elif action_type in (DesktopActionType.SHOW_DESKTOP, DesktopActionType.TASK_VIEW):
            if elapsed < self.gesture_cooldown:
                return
            self._last_action_time = now
            if action_type == DesktopActionType.SHOW_DESKTOP:
                self.executor.show_desktop()
            elif action_type == DesktopActionType.TASK_VIEW:
                self.executor.task_view()

        elif action_type == DesktopActionType.CUSTOM_SHORTCUT:
            if elapsed < self.gesture_cooldown:
                return
            self._last_action_time = now
            self.executor.execute_shortcut(self.custom_shortcut)

    def _build_telemetry(self, gesture_name: str, action_type: DesktopActionType) -> Dict[str, Any]:
        return {
            "mode": "desktop",
            "desktop_active": self._control_active,
            "gesture": gesture_name,
            "desktop_action": self._active_action_name,
            "desktop_state": self._desktop_state.name,
            "cursor_x": int(self._curr_x),
            "cursor_y": int(self._curr_y),
            "is_dragging": self._is_dragging,
            "workspace_w_pct": self.workspace_w_pct,
            "workspace_h_pct": self.workspace_h_pct,
            "show_workspace_overlay": self.show_workspace_overlay,
        }
