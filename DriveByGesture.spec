# -*- mode: python ; coding: utf-8 -*-
# ============================================================================
# DriveByGesture.spec — PyInstaller build specification
#
# Build command:  pyinstaller DriveByGesture.spec --clean
# Output:         dist/DriveByGesture/DriveByGesture.exe  (one-dir bundle)
# ============================================================================

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

# ── mediapipe: collect all internal data files (proto graphs, tflite models)
mediapipe_datas = collect_data_files("mediapipe")

# ── mediapipe: collect compiled DLLs / .so files that it ships internally
mediapipe_binaries = collect_dynamic_libs("mediapipe")

# ── vgamepad: collect ViGEmClient.dll binaries and install resources
vgamepad_binaries = collect_dynamic_libs("vgamepad")
vgamepad_datas = collect_data_files("vgamepad")

# ── opencv: collect its binary data (HAARcascades, etc.)
cv2_datas = collect_data_files("cv2")

# ── PySide6: Qt platform plugin DLLs and translations are handled by the
#    built-in PyInstaller hook for PySide6; no manual action needed.

block_cipher = None

a = Analysis(
    # ── Entry point ──────────────────────────────────────────────────────────
    ["app.py"],

    # ── Extra source paths (all packages live at project root) ───────────────
    pathex=["d:\\Gesture project"],

    # ── Native binaries ──────────────────────────────────────────────────────
    binaries=mediapipe_binaries + vgamepad_binaries,

    # ── Data files / assets ──────────────────────────────────────────────────
    datas=[
        # Application resources (icons, images, branding)
        ("resources",               "resources"),

        # Default configuration TOML
        ("config/default.toml",     "config"),

        # Shipped profile defaults
        ("profiles/active_mode.txt",          "profiles"),
        ("profiles/active_profile.txt",       "profiles"),
        ("profiles/default_calibration.json", "profiles"),

        # MediaPipe hand landmarker model (7.4 MB, critical)
        ("models/hand_landmarker.task",       "models"),

        # mediapipe internal data (proto graphs, tflite models)
        *mediapipe_datas,

        # vgamepad internal data and DLLs
        *vgamepad_datas,

        # opencv internal data (HAARcascades, etc.)
        *cv2_datas,
    ],

    # ── Hidden imports ───────────────────────────────────────────────────────
    # Modules that are imported lazily (inside functions / try-blocks) and
    # therefore not detected automatically by PyInstaller's static analyser.
    hiddenimports=[
        # ── Core stack ──────────────────────────────────────────────────────
        "mediapipe",
        "mediapipe.tasks",
        "mediapipe.tasks.python",
        "mediapipe.tasks.python.vision",
        "mediapipe.tasks.python.components",
        "mediapipe.tasks.python.components.containers",
        "mediapipe.python",
        "mediapipe.python.solutions",
        "cv2",
        "numpy",

        # ── PySide6 modules used at runtime ─────────────────────────────────
        "PySide6",
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "PySide6.QtMultimedia",
        "shiboken6",

        # ── vgamepad ────────────────────────────────────────────────────────
        "vgamepad",

        # ── Lazy-loaded diagnostics / system libs ───────────────────────────
        "psutil",
        "watchdog",
        "watchdog.observers",
        "watchdog.observers.winapi",
        "watchdog.events",

        # ── Project local packages (all must be discoverable) ────────────────
        "actions",
        "analysis",
        "calibration",
        "camera",
        "config",
        "controller",
        "core",
        "core.protocol",
        "desktop",
        "diagnostics",
        "games",
        "games.forza_horizon",
        "gestures",
        "gestures.builtin",
        "gestures.builtins",
        "gestures.custom",
        "gui",
        "logging_system",
        "profiles",
        "tracking",

        # ── stdlib modules sometimes missed ─────────────────────────────────
        "tomllib",
        "urllib.request",
        "threading",
        "json",
    ],

    # ── PyInstaller hook search paths ────────────────────────────────────────
    hookspath=[],
    hooksconfig={},

    # ── Runtime hooks (executed before user code, inside the frozen process) ─
    runtime_hooks=["hook_gesturedrive_models.py"],

    # ── Modules to exclude from the bundle ──────────────────────────────────
    excludes=[
        # Dev / test tools — not needed at runtime
        "pytest",
        "pytest_cov",
        "hypothesis",
        "mypy",
        "ruff",
        # Heavy unused scientific stack
        "scipy",
        "sklearn",
        "pandas",
        "IPython",
        "notebook",
        # Django / Flask not used by DriveByGesture
        "django",
        "flask",
        # Google API / cloud not used at runtime
        "google.api_core",
        "google.auth",
        "google.generativeai",
        "grpc",
    ],

    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],                         # one-dir: binaries go into COLLECT, not EXE
    exclude_binaries=True,      # one-dir mode
    name="DriveByGesture",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                  # UPX can corrupt OpenCV / Qt DLLs — disabled
    console=False,              # windowed GUI app — no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="resources/icons/app.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="DriveByGesture",     # output folder: dist/DriveByGesture/
)
