"""
gesturedrive.gui.help_content
==============================
Help & Documentation Content Provider.
Dynamically retrieves environment runtime info, installed library versions,
and gesture registry metadata to generate structured HTML sections for Help Center.
"""

from __future__ import annotations

import os
import platform
import sys
from typing import Any, Dict, List


from core.version import (
    APP_NAME,
    BUILD_NUMBER,
    COPYRIGHT,
    DEVELOPER,
    LICENSE,
    VERSION,
)


def _get_runtime_info() -> Dict[str, str]:
    """Gather dynamic environment and library metadata."""
    info = {
        "app_name": APP_NAME,
        "version": VERSION,
        "build_number": BUILD_NUMBER,
        "developer": DEVELOPER,
        "python_version": sys.version.split()[0],
        "os_platform": f"{platform.system()} {platform.release()} ({platform.architecture()[0]})",
        "git_commit": BUILD_NUMBER,
        "license": LICENSE,
        "copyright": COPYRIGHT,
    }

    try:
        import cv2
        info["opencv_version"] = cv2.__version__
    except ImportError:
        info["opencv_version"] = "Not Installed"

    try:
        import mediapipe as mp
        info["mediapipe_version"] = getattr(mp, "__version__", "0.10.x")
    except ImportError:
        info["mediapipe_version"] = "Not Installed"

    try:
        import PySide6
        info["pyside_version"] = PySide6.__version__
    except ImportError:
        info["pyside_version"] = "Not Installed"

    return info


def get_help_sections() -> List[Dict[str, Any]]:
    """Return all 10 Help Center sections as structured HTML objects."""
    rt = _get_runtime_info()

    # Dynamic gesture registry extraction for Section 4
    gesture_table_rows = ""
    try:
        from gui.settings_pages import get_implemented_gestures
        gestures = get_implemented_gestures()
        default_mappings = {
            "Open Palm": ("Move Cursor", "Hand position maps relative to active screen workspace"),
            "Pinch": ("Left Click", "Thumb and Index fingertips meet within pinch threshold"),
            "Pinch Pinky": ("Right Click", "Thumb and Pinky fingertips meet within pinch threshold"),
            "Peace": ("Right Click / Secondary", "Index and Middle fingers extended V-shape"),
            "Point": ("Double Click / Select", "Index finger extended, remaining fingers curled"),
            "Fist": ("Click & Drag", "All fingers fully curled into fist"),
            "Thumbs Up": ("Volume Up", "Thumb pointed upward with closed fist"),
            "Thumbs Down": ("Volume Down", "Thumb pointed downward with closed fist"),
        }
        for g_name in gestures:
            act, desc = default_mappings.get(g_name, ("Custom Action", "Recognized gesture mapping"))
            gesture_table_rows += f"<tr><td><b>{g_name}</b></td><td><span class='badge'>{act}</span></td><td>{desc}</td></tr>\n"
    except Exception:
        gesture_table_rows = """
        <tr><td><b>Open Palm</b></td><td><span class='badge'>Move Cursor</span></td><td>Position maps to active screen workspace</td></tr>
        <tr><td><b>Pinch</b></td><td><span class='badge'>Left Click</span></td><td>Thumb + Index pinch trigger</td></tr>
        <tr><td><b>Pinch Pinky</b></td><td><span class='badge'>Right Click</span></td><td>Thumb + Pinky pinch trigger</td></tr>
        <tr><td><b>Peace</b></td><td><span class='badge'>Right Click</span></td><td>Index + Middle V-shape extension</td></tr>
        <tr><td><b>Point</b></td><td><span class='badge'>Double Click</span></td><td>Index extended pointing gesture</td></tr>
        <tr><td><b>Fist</b></td><td><span class='badge'>Drag</span></td><td>Closed fist hold gesture</td></tr>
        <tr><td><b>Thumbs Up</b></td><td><span class='badge'>Volume Up</span></td><td>Thumb pointed upward</td></tr>
        <tr><td><b>Thumbs Down</b></td><td><span class='badge'>Volume Down</span></td><td>Thumb pointed downward</td></tr>
        """

    sections = [
        # 1. About DriveByGesture
        {
            "id": "about",
            "title": "1. About DriveByGesture",
            "icon": "ℹ️",
            "html": f"""
            <h2>About DriveByGesture</h2>
            <p class="lead">DriveByGesture is a state-of-the-art computer vision platform enabling touchless steering control for racing simulators and full hands-free Windows desktop navigation using standard webcams.</p>
            
            <div class="card">
                <h3>System & Build Information</h3>
                <table>
                    <tr><th>Application Name</th><td>{rt['app_name']}</td></tr>
                    <tr><th>Version</th><td><b style="color: #00e5ff;">v{rt['version']}</b></td></tr>
                    <tr><th>Build Number</th><td>{rt['build_number']}</td></tr>
                    <tr><th>Developer</th><td>{rt['developer']}</td></tr>
                    <tr><th>Operating System</th><td>{rt['os_platform']}</td></tr>
                    <tr><th>Git Commit</th><td><code>{rt['git_commit']}</code></td></tr>
                    <tr><th>License</th><td>{rt['license']}</td></tr>
                    <tr><th>Copyright</th><td>{rt['copyright']}</td></tr>
                </table>
            </div>

            <div class="card">
                <h3>Core Dependency Engine Versions</h3>
                <table>
                    <tr><th>Python Interpreter</th><td>{rt['python_version']}</td></tr>
                    <tr><th>OpenCV (Vision Processing)</th><td>{rt['opencv_version']}</td></tr>
                    <tr><th>Google MediaPipe (3D Tracking)</th><td>{rt['mediapipe_version']}</td></tr>
                    <tr><th>PySide6 / Qt (GUI Framework)</th><td>{rt['pyside_version']}</td></tr>
                </table>
            </div>
            """
        },

        # 2. Getting Started
        {
            "id": "getting_started",
            "title": "2. Getting Started",
            "icon": "🚀",
            "html": """
            <h2>Getting Started Guide</h2>
            <p>Follow these core steps to get up and running with DriveByGesture in under two minutes.</p>

            <ol class="step-list">
                <li>
                    <b>First Launch & Camera Feed:</b>
                    Connect your USB webcam or integrated camera. DriveByGesture auto-detects device index 0. If using an external camera, open <i>Settings → Camera</i> and select your preferred device.
                </li>
                <li>
                    <b>Steering Calibration:</b>
                    Before driving, launch the <i>Calibration Wizard</i> from the main dashboard or <i>Settings → Calibration</i>. Follow the 3-step prompt to set Center baseline, Left lock angle, and Right lock angle.
                </li>
                <li>
                    <b>Operating Mode Selection:</b>
                    Use the mode selector in the top bar to switch between:
                    <ul>
                        <li><b>🚗 Driving Mode:</b> Emulates a physical Xbox 360 controller with smooth analog steering and throttle/brake triggers.</li>
                        <li><b>🖥️ Desktop Mode:</b> Controls Windows mouse cursor, clicks, scrolling, and custom keyboard shortcuts hands-free.</li>
                    </ul>
                </li>
                <li>
                    <b>Profile Management:</b>
                    Save your custom deadzones, lock angles, and gesture mappings into dedicated profiles (e.g., <i>Forza 5</i>, <i>Assetto Corsa</i>, <i>Desktop Work</i>) via <i>Settings → Profiles</i>.
                </li>
            </ol>
            """
        },

        # 3. Driving Mode Guide
        {
            "id": "driving_mode",
            "title": "3. Driving Mode Guide",
            "icon": "🏎️",
            "html": """
            <h2>Driving Mode Guide</h2>
            <p>Driving Mode converts hand tilt rotation into ultra-precise analog Xbox controller steering inputs.</p>

            <div class="card">
                <h3>Steering Controls</h3>
                <ul>
                    <li><b>Steering Angle:</b> Hold your hand upright in front of the camera. Tilt your hand left to turn left; tilt right to turn right.</li>
                    <li><b>Accelerator / Throttle:</b> Open Palm gesture acts as full accelerator pedal.</li>
                    <li><b>Brake:</b> Closed Fist gesture acts as brake pedal.</li>
                    <li><b>Handbrake:</b> Pinch gesture triggers handbrake (A button / RB).</li>
                </ul>
            </div>

            <div class="card">
                <h3>Controller Emulation & Compatibility</h3>
                <p>DriveByGesture uses the <b>ViGEmBus</b> kernel driver to emulate an official Virtual Xbox 360 controller. Supported out of the box in:</p>
                <ul>
                    <li>Forza Horizon 4 & 5 / Forza Motorsport</li>
                    <li>Assetto Corsa & Assetto Corsa Competizione</li>
                    <li>Euro Truck Simulator 2 & American Truck Simulator</li>
                    <li>Dirt Rally 2.0 & EA Sports WRC</li>
                    <li>Need for Speed (Unbound, Heat)</li>
                    <li>BeamNG.drive</li>
                </ul>
            </div>

            <div class="card">
                <h3>Recommended Camera Position</h3>
                <p>Place your webcam directly above or below your monitor at eye level, facing straight towards your driving seating position at a distance of <b>0.5m to 1.2m</b>.</p>
            </div>
            """
        },

        # 4. Desktop Mode Guide
        {
            "id": "desktop_mode",
            "title": "4. Desktop Mode Guide",
            "icon": "🖥️",
            "html": f"""
            <h2>Desktop Mode Guide</h2>
            <p>Desktop Mode allows full hands-free navigation of Windows applications, browsers, and media players.</p>

            <div class="card">
                <h3>Implemented Gesture Registry</h3>
                <table>
                    <thead>
                        <tr><th>Gesture</th><th>Action Binding</th><th>Trigger Description</th></tr>
                    </thead>
                    <tbody>
                        {gesture_table_rows}
                    </tbody>
                </table>
            </div>

            <div class="card">
                <h3>Workspace Bounds & Smoothing</h3>
                <p>Customize <i>Horizontal Workspace %</i> (e.g. 80%) and <i>Vertical Workspace %</i> in <i>Settings → Desktop Controls</i> to control how much hand motion is required to reach screen edges.</p>
            </div>
            """
        },

        # 5. Settings Guide
        {
            "id": "settings_guide",
            "title": "5. Settings Guide",
            "icon": "⚙️",
            "html": """
            <h2>Settings & Configuration Guide</h2>
            <p>Every configurable option in DriveByGesture is categorized into 7 dedicated settings pages:</p>

            <div class="card">
                <h3>Settings Categories Overview</h3>
                <table>
                    <tr><th>Page Name</th><th>What It Controls</th><th>Recommended Defaults</th></tr>
                    <tr><td><b>General</b></td><td>Auto-save calibration on exit, auto-start pipeline on app launch</td><td>Auto-save Enabled</td></tr>
                    <tr><td><b>Camera</b></td><td>Device index, capture resolution, FPS, mirror preview, HUD overlay</td><td>1280x720 @ 30 FPS, Mirror Enabled</td></tr>
                    <tr><td><b>Steering</b></td><td>Sensitivity, Deadzone, Max lock angle, EMA smoothing, Steering inversion</td><td>Sensitivity 1.0x, Deadzone 0.05, Lock 30°</td></tr>
                    <tr><td><b>Controller</b></td><td>ViGEmBus Xbox 360 controller emulation vs Null safe mode</td><td>Virtual Xbox 360 Controller</td></tr>
                    <tr><td><b>Desktop Controls</b></td><td>Cursor speed, smoothing, deadzone, workspace %, gesture bindings table</td><td>Sensitivity 1.75, Smoothing 0.25, Workspace 80%</td></tr>
                    <tr><td><b>Profiles</b></td><td>Full CRUD profile management, JSON Import/Export, Active profile selection</td><td>Default Profile</td></tr>
                    <tr><td><b>Calibration</b></td><td>Baseline status, Wizard launcher, Reset defaults</td><td>Calibrated Status</td></tr>
                </table>
            </div>
            """
        },

        # 6. Calibration Guide
        {
            "id": "calibration_guide",
            "title": "6. Calibration Guide",
            "icon": "🎯",
            "html": """
            <h2>Steering Calibration Guide</h2>
            <p>Calibration adapts DriveByGesture to your personal hand range of motion, seating distance, and webcam angle.</p>

            <div class="card">
                <h3>Why Calibration Matters</h3>
                <p>Without calibration, steering normalizes against a static 30° lock. Calibration maps your natural <b>Left Max Tilt</b>, <b>Center Neutral</b>, and <b>Right Max Tilt</b> for perfect 1:1 steering linearity.</p>
            </div>

            <div class="card">
                <h3>Best Practices & Environment Tips</h3>
                <ul>
                    <li><b>Lighting:</b> Ensure your room is well lit. Avoid strong sunlight or direct lamps directly behind your head (backlight).</li>
                    <li><b>Hand Position:</b> Keep your wrist visible to the camera. Do not block your palm with your other hand.</li>
                    <li><b>Camera Distance:</b> Sit between 0.5 meters and 1.2 meters from the camera lens.</li>
                    <li><b>Common Mistake:</b> Tilting your head or body instead of turning your wrist. Only your wrist/hand needs to rotate.</li>
                </ul>
            </div>
            """
        },

        # 7. Troubleshooting
        {
            "id": "troubleshooting",
            "title": "7. Troubleshooting",
            "icon": "🛠️",
            "html": """
            <h2>Troubleshooting & Diagnostics</h2>
            <p>Quick solutions for common hardware, vision, and driver issues.</p>

            <div class="card">
                <h3>Issue 1: Camera Feed is Blank or Not Detected</h3>
                <p><b>Cause:</b> Camera index mismatch or another application (Zoom, Teams, OBS) is holding exclusive lock on the camera.</p>
                <p><b>Solution:</b> Close other vision software, go to <i>Settings → Camera</i>, and change the device dropdown from 0 to 1 or 2.</p>
            </div>

            <div class="card">
                <h3>Issue 2: Virtual Xbox Controller Not Found in Game</h3>
                <p><b>Cause:</b> ViGEmBus kernel driver is missing or virtual device was disconnected.</p>
                <p><b>Solution:</b> Open <i>Settings → Controller</i> and click <b>🔌 Reconnect Controller</b>. If using safe mode, ensure ViGEmBus driver is installed on Windows.</p>
            </div>

            <div class="card">
                <h3>Issue 3: Steering Turned Left Goes Right (Inverted)</h3>
                <p><b>Cause:</b> Mirror camera preview mode or inverted axis setting.</p>
                <p><b>Solution:</b> Open <i>Settings → Steering</i> and toggle the <b>Invert Steering Direction</b> checkbox.</p>
            </div>

            <div class="card">
                <h3>Issue 4: Desktop Mode Gestures Not Firing</h3>
                <p><b>Cause:</b> Application is still in Driving Mode or gesture confidence is below threshold.</p>
                <p><b>Solution:</b> Check top bar indicator and switch mode to <b>🖥️ Desktop Mode</b>.</p>
            </div>
            """
        },

        # 8. Keyboard Shortcuts
        {
            "id": "shortcuts",
            "title": "8. Keyboard Shortcuts",
            "icon": "⌨️",
            "html": """
            <h2>Keyboard Shortcuts Reference</h2>
            <p>Supported keyboard shortcuts across the application and desktop bindings.</p>

            <div class="card">
                <h3>Default Action Shortcuts</h3>
                <table>
                    <tr><th>Shortcut Sequence</th><th>Function / Action</th><th>Configurable Location</th></tr>
                    <tr><td><code>Ctrl + Tab</code></td><td>Cycle Operating Mode / Custom Shortcut trigger</td><td>Settings → Desktop Controls</td></tr>
                    <tr><td><code>Ctrl + C</code></td><td>Copy Selection Preset</td><td>Desktop Preset Toolbar</td></tr>
                    <tr><td><code>Ctrl + V</code></td><td>Paste Clipboard Preset</td><td>Desktop Preset Toolbar</td></tr>
                    <tr><td><code>Ctrl + Z</code></td><td>Undo Action Preset</td><td>Desktop Preset Toolbar</td></tr>
                    <tr><td><code>Win + D</code></td><td>Toggle Minimize All / Show Desktop</td><td>Desktop Preset Toolbar</td></tr>
                    <tr><td><code>Alt + Tab</code></td><td>Windows Task Switcher</td><td>Desktop Preset Toolbar</td></tr>
                    <tr><td><code>Ctrl + Shift + Esc</code></td><td>Open Windows Task Manager</td><td>Desktop Preset Toolbar</td></tr>
                </table>
            </div>
            """
        },

        # 9. Changelog
        {
            "id": "changelog",
            "title": "9. Changelog & Version History",
            "icon": "📜",
            "html": """
            <h2>Version History & Release Notes</h2>

            <div class="card">
                <h3>v1.0.0 (Release Candidate) — 2026.08.03</h3>
                <ul>
                    <li><b>Complete Profile Management:</b> Full CRUD operations (Create, Rename, Duplicate, Delete, Import, Export, Set Active, Restore Default) with JSON schema validation.</li>
                    <li><b>Settings Audit:</b> Mouse wheel scroll protection on all dropdowns, sliders, and spinboxes across settings dialog.</li>
                    <li><b>Coordinate System Alignment:</b> Vector parity for wrist/MCP hand tilt angles across calibration and action engine.</li>
                    <li><b>Virtual Controller System:</b> Xbox 360 controller emulation with ViGEmBus and Null fallback mode.</li>
                    <li><b>Help & Documentation Center:</b> Integrated 10-section searchable documentation hub with HTML export capability.</li>
                </ul>
            </div>

            <div class="card">
                <h3>v0.9.0 (Beta Feature Freeze) — 2026.07.26</h3>
                <ul>
                    <li>Initial MediaPipe 3D Landmark integration & 21-point tracking pipeline.</li>
                    <li>PySide6 modern dark mode UI layout with live telemetry overlays.</li>
                </ul>
            </div>
            """
        },

        # 10. Credits
        {
            "id": "credits",
            "title": "10. Credits & Open Source",
            "icon": "👏",
            "html": """
            <h2>Credits & Open Source Acknowledgments</h2>
            <p>DriveByGesture is built on top of world-class open-source software libraries and frameworks.</p>

            <div class="card">
                <h3>Core Open Source Libraries</h3>
                <table>
                    <tr><th>Library / Project</th><th>Author / Maintainer</th><th>License</th><th>Role in DriveByGesture</th></tr>
                    <tr><td><b>Google MediaPipe</b></td><td>Google Deepmind</td><td>Apache 2.0</td><td>3D Hand landmark tracking & gesture inference</td></tr>
                    <tr><td><b>OpenCV</b></td><td>OpenCV Team</td><td>Apache 2.0</td><td>Camera video frame capture & image transformations</td></tr>
                    <tr><td><b>PySide6 (Qt for Python)</b></td><td>The Qt Company</td><td>LGPL v3</td><td>Modern graphical interface, layout, and stylesheet engine</td></tr>
                    <tr><td><b>ViGEmBus / vgamepad</b></td><td>Nefarius Software Solutions</td><td>MIT License</td><td>Kernel-level Virtual Xbox 360 controller output bus</td></tr>
                    <tr><td><b>NumPy</b></td><td>NumPy Developers</td><td>BSD License</td><td>High-performance vector mathematics & array processing</td></tr>
                </table>
            </div>

            <div class="card">
                <p style="text-align: center; color: #8f96a3; font-size: 11px;">
                    Thank you to the global open-source community for making hands-free human-computer interaction possible.
                </p>
            </div>
            """
        },
    ]

    return sections
