================================================================================
  DriveByGesture — Installation & Usage Guide
  Version 1.0.0  |  Build 2026.08.03-RC1
================================================================================

OVERVIEW
--------
DriveByGesture lets you control PC racing games using real-time hand gestures
captured through your webcam.  No Python installation is required to run the
distributed EXE.


HOW TO RUN
----------
1. Extract the DriveByGesture folder to any location (e.g. Desktop, C:\Games\).
2. Double-click  DriveByGesture.exe  inside the extracted folder.
3. A splash screen will appear, followed by the main Control Center window.

  NOTE: Do NOT move DriveByGesture.exe out of its folder. The EXE depends on
  the DLL files and asset folders that sit alongside it.  Always run the EXE
  from inside the DriveByGesture\ folder, or create a shortcut that points to
  the EXE in its original location.


SYSTEM REQUIREMENTS
-------------------
  Operating System : Windows 10 / 11  (64-bit)
  Python           : NOT required — all dependencies are bundled
  RAM              : 4 GB minimum, 8 GB recommended
  CPU              : Any modern x64 processor
  Webcam           : Any USB or built-in webcam (720p or higher recommended)
  GPU              : Not required (MediaPipe runs on CPU)


PREREQUISITE: ViGEmBus Driver  (REQUIRED for Xbox Controller Output)
---------------------------------------------------------------------
DriveByGesture emulates an Xbox 360 controller to send input to games.
This requires the ViGEmBus kernel driver to be installed on your PC.

  DOWNLOAD: https://github.com/nefarius/ViGEmBus/releases
            (download the latest  ViGEmBus_Setup_x64.exe  and run it)

  - If ViGEmBus is NOT installed, DriveByGesture will still launch and the
    camera/gesture tracking will function, but no controller input will be
    sent to games.
  - The application will show a "Controller Unavailable" status in the UI
    rather than crashing.
  - Install ViGEmBus, then restart DriveByGesture.


WEBCAM PERMISSION
-----------------
DriveByGesture requires access to your webcam for gesture tracking.

  - On first launch, Windows may show a camera access prompt — click  Allow.
  - If your webcam is in use by another application (e.g. a video call), close
    that application first, then restart DriveByGesture.
  - If no webcam is detected, the Camera widget in the UI will show an error.
    Plug in a USB webcam and restart the application.
  - You can select which camera index to use in Settings → Camera.


WINDOWS DEFENDER / ANTIVIRUS
-----------------------------
Because DriveByGesture is a packaged Python application, some antivirus tools
may flag it as "suspicious" (false positive — a known issue with PyInstaller
EXEs).

  If Windows Defender SmartScreen blocks the launch:
  1. Click  "More info"  on the SmartScreen dialog.
  2. Click  "Run anyway".

  Or right-click  DriveByGesture.exe → Properties → check "Unblock" → OK.


FIRST LAUNCH — WHAT TO EXPECT
-------------------------------
1. A dark splash screen loads while the application initialises.
2. The main Control Center window opens with:
     - Camera feed panel (live webcam preview)
     - Gesture recognition status
     - Controller output status
     - Profile selector
3. To start gesture control: click  Start  in the Control Panel.
4. To configure gestures or camera settings: open the  Settings  dialog.
5. To run the calibration wizard: click  Calibrate  in the top bar.


COMMON ISSUES
-------------
Q: The EXE doesn't start / immediately closes.
A: Check that all files from the DriveByGesture\ folder are present.
   Right-click the EXE and choose "Run as administrator" if it still fails.

Q: "Camera not found" error.
A: Ensure your webcam is plugged in and not used by another app.
   In Settings → Camera, try changing the Camera Index from 0 to 1 or 2.

Q: No controller input reaches my game.
A: Install the ViGEmBus driver (see above), then restart DriveByGesture.

Q: The gesture model fails to load.
A: Ensure  models\hand_landmarker.task  is present inside the DriveByGesture\
   folder.  If it is missing, re-extract the ZIP distribution.

Q: High CPU usage.
A: MediaPipe hand tracking is CPU-intensive.  In Settings → Tracking, reduce
   "Max Hands" to 1, or lower the camera FPS to reduce CPU load.


CRASH REPORTS, LOGS & USER DATA
----------------------------------
DriveByGesture stores all user profiles, runtime logs, and crash reports in:

    %LOCALAPPDATA%\DriveByGesture\
    ├── profiles\
    ├── logs\
    └── crash_reports\

Include the latest log or crash report file when reporting issues.


PROJECT & SOURCE CODE
---------------------
  GitHub : https://github.com/adhil-vt/DriveByGesture
  License: MIT License  —  © 2026 DriveByGesture Project


================================================================================
