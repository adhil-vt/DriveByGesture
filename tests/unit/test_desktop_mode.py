"""
tests/unit/test_desktop_mode.py
================================
Unit tests for Phase 12 Desktop Gesture Mode components.
"""

from pathlib import Path
import tempfile
import pytest

from desktop.enums import AppMode, DesktopActionType
from desktop.actions import DesktopAction
from desktop.executor import NullDesktopExecutor, WindowsDesktopExecutor, get_desktop_executor
from desktop.bindings import GestureBindingManager, default_gesture_bindings
from desktop.controller import DesktopController
from desktop.manager import ModeManager
from profiles.profile import DriveProfile, ProfileMetadata


def test_desktop_enums():
    assert AppMode.from_str("driving") == AppMode.DRIVING
    assert AppMode.from_str("DESKTOP") == AppMode.DESKTOP
    assert AppMode.from_str("invalid") == AppMode.DRIVING

    assert DesktopActionType.from_str("move_cursor") == DesktopActionType.MOVE_CURSOR
    assert DesktopActionType.from_str("LEFT_CLICK") == DesktopActionType.LEFT_CLICK
    assert DesktopActionType.from_str("invalid_action") == DesktopActionType.NONE


def test_desktop_action_model():
    act = DesktopAction(action_type=DesktopActionType.LEFT_CLICK, value=1.0, confidence=0.95)
    assert act.action_type == DesktopActionType.LEFT_CLICK
    assert act.confidence == 0.95


def test_desktop_executors():
    executor = get_desktop_executor()
    assert executor is not None
    w, h = executor.get_screen_size()
    assert w > 0 and h > 0

    null_exec = NullDesktopExecutor()
    null_exec.set_cursor_pos(100, 200)
    null_exec.left_click()
    null_exec.scroll(1)
    null_exec.volume_up()
    null_exec.show_desktop()
    null_exec.execute_shortcut("ctrl+c")


def test_gesture_binding_manager():
    mgr = GestureBindingManager()
    assert mgr.resolve_action("Open Palm") == DesktopActionType.MOVE_CURSOR
    assert mgr.resolve_action("Pinch") == DesktopActionType.LEFT_CLICK
    assert mgr.resolve_action("Peace") == DesktopActionType.RIGHT_CLICK
    assert mgr.resolve_action("Unknown") == DesktopActionType.NONE

    mgr.bind("Open Palm", "VOLUME_UP")
    assert mgr.resolve_action("Open Palm") == DesktopActionType.VOLUME_UP

    d = mgr.to_dict()
    assert d["Open Palm"] == "VOLUME_UP"

    mgr.reset_defaults()
    assert mgr.resolve_action("Open Palm") == DesktopActionType.MOVE_CURSOR


def test_desktop_controller():
    exec_stub = NullDesktopExecutor()
    controller = DesktopController(executor=exec_stub)
    assert controller.cursor_sensitivity == 1.75

    # Process empty hands
    telem = controller.process([], [], [])
    assert telem["mode"] == "desktop"
    assert not telem["desktop_active"]

    # Process hand landmarks
    class MockLandmark:
        def __init__(self, x, y):
            self.x = x
            self.y = y

    class MockHand:
        def __init__(self, x=0.5, y=0.5):
            self.landmarks = [MockLandmark(x, y) for _ in range(21)]

    class MockGestureResult:
        def __init__(self, name, detected=True):
            self.gesture_name = name
            self.detected = detected
            self.confidence = 0.9

    hand = MockHand(0.5, 0.5)
    g_res = MockGestureResult("Open Palm")

    telem = controller.process([hand], [], [g_res])
    assert telem["desktop_active"]
    assert telem["gesture"] == "Open Palm"
    assert telem["desktop_action"] == "Move Cursor"


def test_desktop_controller_coordinate_mapping():
    """Verify hand RIGHT maps to cursor RIGHT, hand LEFT maps to cursor LEFT, UP/DOWN correct."""
    exec_stub = NullDesktopExecutor()
    controller = DesktopController(executor=exec_stub)
    w, h = exec_stub.get_screen_size()

    class MockLandmark:
        def __init__(self, x, y):
            self.x = x
            self.y = y

    class MockHand:
        def __init__(self, x, y):
            self.landmarks = [MockLandmark(x, y) for _ in range(21)]

    class MockGestureResult:
        def __init__(self):
            self.gesture_name = "Open Palm"
            self.detected = True
            self.confidence = 0.9

    # Hand moves physical RIGHT -> camera x is small (e.g. 0.1) -> cursor x should be on RIGHT half (> w / 2)
    controller._curr_x = float(w // 2)
    controller._curr_y = float(h // 2)
    hand_right = MockHand(x=0.1, y=0.5)
    telem = controller.process([hand_right], [], [MockGestureResult()])
    assert telem["cursor_x"] > (w / 2), f"Expected cursor on right half, got cursor_x={telem['cursor_x']}"

    # Hand moves physical LEFT -> camera x is large (e.g. 0.9) -> cursor x should be on LEFT half (< w / 2)
    controller._curr_x = float(w // 2)
    controller._curr_y = float(h // 2)
    hand_left = MockHand(x=0.9, y=0.5)
    telem = controller.process([hand_left], [], [MockGestureResult()])
    assert telem["cursor_x"] < (w / 2), f"Expected cursor on left half, got cursor_x={telem['cursor_x']}"

    # Hand moves physical UP -> camera y is small (e.g. 0.1) -> cursor y should be on TOP half (< h / 2)
    controller._curr_x = float(w // 2)
    controller._curr_y = float(h // 2)
    hand_up = MockHand(x=0.5, y=0.1)
    telem = controller.process([hand_up], [], [MockGestureResult()])
    assert telem["cursor_y"] < (h / 2), f"Expected cursor on top half, got cursor_y={telem['cursor_y']}"

    # Hand moves physical DOWN -> camera y is large (e.g. 0.9) -> cursor y should be on BOTTOM half (> h / 2)
    controller._curr_x = float(w // 2)
    controller._curr_y = float(h // 2)
    hand_down = MockHand(x=0.5, y=0.9)
    telem = controller.process([hand_down], [], [MockGestureResult()])
    assert telem["cursor_y"] > (h / 2), f"Expected cursor on bottom half, got cursor_y={telem['cursor_y']}"


def test_mode_manager():
    from core.resources import get_active_mode_path

    cb_calls = []

    def on_change(mode):
        cb_calls.append(mode)

    state_file = get_active_mode_path()
    if state_file.exists():
        state_file.unlink()

    mgr = ModeManager(initial_mode=AppMode.DRIVING, on_mode_changed=on_change)
    assert mgr.active_mode == AppMode.DRIVING
    assert mgr.is_driving_active
    assert not mgr.is_desktop_active

    mgr.set_mode("desktop")
    assert mgr.active_mode == AppMode.DESKTOP
    assert mgr.is_desktop_active
    assert len(cb_calls) == 1
    assert cb_calls[0] == AppMode.DESKTOP

    mgr.toggle_mode()
    assert mgr.active_mode == AppMode.DRIVING
    assert len(cb_calls) == 2


def test_drive_profile_desktop_serialization():
    p = DriveProfile.create_default()
    assert "cursor_sensitivity" in p.desktop
    assert p.desktop["cursor_sensitivity"] == 1.75

    d = p.to_dict()
    assert "desktop" in d
    assert d["desktop"]["mode"] == "driving"

    p2 = DriveProfile.from_dict(d)
    assert p2.desktop["cursor_sensitivity"] == 1.75


def test_drag_anchor_lock_and_release_hysteresis():
    """Verify cursor does not jump when drag starts and drag persists through 3-frame release guard."""
    exec_stub = NullDesktopExecutor()
    controller = DesktopController(executor=exec_stub)
    w, h = exec_stub.get_screen_size()

    class MockLandmark:
        def __init__(self, x, y):
            self.x = x
            self.y = y

    class MockHand:
        def __init__(self, x, y):
            self.landmarks = [MockLandmark(x, y) for _ in range(21)]

    class MockGestureResult:
        def __init__(self, name, detected=True):
            self.gesture_name = name
            self.detected = detected
            self.confidence = 0.9

    controller._curr_x = 500.0
    controller._curr_y = 500.0

    # Start Drag with Pinch gesture
    hand_pinch = MockHand(x=0.3, y=0.3)
    g_pinch = MockGestureResult("Pinch")

    telem1 = controller.process([hand_pinch], [], [g_pinch])
    assert telem1["is_dragging"], "Pinch should trigger dragging"
    assert telem1["cursor_x"] == 500, f"Cursor must not jump on drag start, expected 500, got {telem1['cursor_x']}"

    # Transient missing gesture frame 1
    telem2 = controller.process([hand_pinch], [], [MockGestureResult("Unknown", detected=False)])
    assert telem2["is_dragging"], "Drag must persist across frame 1 of noise"

    # Transient missing gesture frame 2
    telem3 = controller.process([hand_pinch], [], [MockGestureResult("Unknown", detected=False)])
    assert telem3["is_dragging"], "Drag must persist across frame 2 of noise"

    # Transient missing gesture frame 3 (3rd frame triggers release)
    telem4 = controller.process([hand_pinch], [], [MockGestureResult("Unknown", detected=False)])
    assert not telem4["is_dragging"], "3rd release frame must call mouse_up and end drag"


def test_finger_articulation_lock_zero_drift():
    """Verify flexing index finger to pinch causes zero cursor drift when target is locked."""
    exec_stub = NullDesktopExecutor()
    controller = DesktopController(executor=exec_stub)
    w, h = exec_stub.get_screen_size()

    class MockLandmark:
        def __init__(self, x, y):
            self.x = x
            self.y = y

    class MockHand:
        def __init__(self, thumb_x, thumb_y, index_x, index_y):
            # Create 21 landmarks with thumb (4) and index (8) at specific positions
            self.landmarks = [MockLandmark(0.5, 0.5) for _ in range(21)]
            self.landmarks[0] = MockLandmark(0.5, 0.7)   # Wrist
            self.landmarks[4] = MockLandmark(thumb_x, thumb_y)  # Thumb tip
            self.landmarks[5] = MockLandmark(0.5, 0.5)   # Index MCP
            self.landmarks[8] = MockLandmark(index_x, index_y)  # Index tip
            self.landmarks[9] = MockLandmark(0.5, 0.4)   # Middle MCP
            self.landmarks[17] = MockLandmark(0.6, 0.5)  # Pinky MCP

    controller._curr_x = 400.0
    controller._curr_y = 400.0

    # User initiates pinch approach (thumb & index tip approaching each other, norm_pinch_dist ~0.45 * scale)
    hand_approach = MockHand(thumb_x=0.468, thumb_y=0.468, index_x=0.532, index_y=0.532)
    telem_approach = controller.process([hand_approach], [], [])

    assert telem_approach["desktop_state"] == "ARTICULATION_LOCK"
    assert telem_approach["cursor_x"] == 400, "Cursor must remain locked at target during finger articulation approach"


def test_active_workspace_mapping():
    """Verify active workspace (80% W, 80% H) maps 10% camera bounds to 0 and 90% camera bounds to max screen."""
    exec_stub = NullDesktopExecutor()
    controller = DesktopController(executor=exec_stub)
    w, h = exec_stub.get_screen_size()

    controller.workspace_w_pct = 0.80
    controller.workspace_h_pct = 0.80
    controller.cursor_smoothing = 1.0  # Instant update for test assertion
    controller.cursor_acceleration = False

    class MockLandmark:
        def __init__(self, x, y):
            self.x = x
            self.y = y

    class MockHand:
        def __init__(self, x, y):
            self.landmarks = [MockLandmark(0.5, 0.5) for _ in range(21)]
            self.landmarks[8] = MockLandmark(x, y)  # Index tip

    # Hand at 90% camera x (inverted -> 10% camera bounds -> left edge of workspace)
    hand_left = MockHand(x=0.90, y=0.50)
    telem_left = controller.process([hand_left], [], [])
    assert telem_left["cursor_x"] == 0, f"Expected 0 at left workspace bound, got {telem_left['cursor_x']}"

    # Hand at 10% camera x (inverted -> 90% camera bounds -> right edge of workspace)
    hand_right = MockHand(x=0.10, y=0.50)
    telem_right = controller.process([hand_right], [], [])
    assert telem_right["cursor_x"] == w - 1, f"Expected {w-1} at right workspace bound, got {telem_right['cursor_x']}"




