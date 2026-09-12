@echo off
REM ============================================================================
REM  DriveByGesture — Windows EXE Build Script
REM  Usage: build_exe.bat
REM  Output: dist\DriveByGesture\DriveByGesture.exe
REM          dist\DriveByGesture.zip
REM ============================================================================

setlocal EnableDelayedExpansion

REM Change to script directory (project root)
cd /d "%~dp0"

echo.
echo ============================================================
echo  DriveByGesture — EXE Build
echo  Python: %PYTHON%
echo ============================================================
echo.

REM ── Verify pyinstaller is available ─────────────────────────────────────────
pyinstaller --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] pyinstaller not found. Install it with:
    echo         pip install pyinstaller
    exit /b 1
)

REM ── Clean previous build ────────────────────────────────────────────────────
echo [1/4] Cleaning previous build artifacts...
if exist "dist\DriveByGesture" (
    rmdir /s /q "dist\DriveByGesture"
    echo       Removed dist\DriveByGesture
)
if exist "dist\DriveByGesture.zip" (
    del /f /q "dist\DriveByGesture.zip"
    echo       Removed dist\DriveByGesture.zip
)

REM ── Run PyInstaller ─────────────────────────────────────────────────────────
echo.
echo [2/4] Running PyInstaller...
echo       Spec: DriveByGesture.spec
echo.

pyinstaller DriveByGesture.spec --clean --noconfirm
if errorlevel 1 (
    echo.
    echo [ERROR] PyInstaller build FAILED. Check output above for details.
    exit /b 1
)

REM ── Verify output ───────────────────────────────────────────────────────────
echo.
echo [3/4] Verifying build output...

if not exist "dist\DriveByGesture\DriveByGesture.exe" (
    echo [ERROR] DriveByGesture.exe not found in dist\DriveByGesture\
    exit /b 1
)

if not exist "dist\DriveByGesture\models\hand_landmarker.task" (
    echo [WARNING] hand_landmarker.task not found in dist\DriveByGesture\models\
    echo           The application will attempt to download it on first launch.
) else (
    echo       OK: hand_landmarker.task bundled
)

if not exist "dist\DriveByGesture\config\default.toml" (
    echo [WARNING] default.toml not found in dist\DriveByGesture\config\
) else (
    echo       OK: config\default.toml bundled
)

echo       OK: DriveByGesture.exe found

REM ── Copy README_INSTALL.txt into dist folder ─────────────────────────────────
if exist "README_INSTALL.txt" (
    copy /y "README_INSTALL.txt" "dist\DriveByGesture\README_INSTALL.txt" >nul
    echo       OK: README_INSTALL.txt copied to dist\DriveByGesture\
)

REM ── ZIP the dist folder ──────────────────────────────────────────────────────
echo.
echo [4/4] Creating ZIP archive...
echo       Source : dist\DriveByGesture\
echo       Target : dist\DriveByGesture.zip

REM Use PowerShell's Compress-Archive (available on Win10+)
powershell -NoProfile -Command ^
    "Compress-Archive -Path 'dist\DriveByGesture' -DestinationPath 'dist\DriveByGesture.zip' -Force" ^
    2>&1

if errorlevel 1 (
    echo [WARNING] ZIP creation failed. The EXE folder is still usable at dist\DriveByGesture\
) else (
    echo       OK: dist\DriveByGesture.zip created
)

REM ── Print summary ────────────────────────────────────────────────────────────
echo.
echo ============================================================
echo  BUILD COMPLETE
echo ============================================================
echo.
echo  EXE   : %~dp0dist\DriveByGesture\DriveByGesture.exe
echo  ZIP   : %~dp0dist\DriveByGesture.zip
echo.
echo  To rebuild later, run:
echo    cd /d "%~dp0"
echo    pyinstaller DriveByGesture.spec --clean --noconfirm
echo.
echo  To test the EXE now, run:
echo    dist\DriveByGesture\DriveByGesture.exe
echo.

REM ── Optional: ask user if they want to launch the EXE ────────────────────────
set /p LAUNCH="  Launch DriveByGesture.exe now for a smoke test? (y/N): "
if /i "!LAUNCH!"=="y" (
    echo.
    echo  Launching dist\DriveByGesture\DriveByGesture.exe ...
    start "" "dist\DriveByGesture\DriveByGesture.exe"
)

echo.
echo  Done.
endlocal
