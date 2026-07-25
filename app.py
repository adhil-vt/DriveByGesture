"""
gesturedrive.app
=================
Application: the top-level orchestrator that wires all subsystems together.

This is the only place in the codebase where concrete classes are
instantiated and injected. All other modules depend only on interfaces.

Startup sequence (see Architecture §13)
-----------------------------------------
1.  Configure logging
2.  Load and validate configuration
3.  Create EventBus
4.  Run HealthCheck (abort on critical failure)
5.  Discover game plugins
6.  Load user profile (create default if missing)
7.  Load calibration profile (schedule wizard if missing)
8.  Wire the processing pipeline (DI)
9.  Wire EventBus subscriptions
10. Build and show the UI
11. Start the CaptureLoop daemon thread

Shutdown sequence
-----------------
A. CaptureLoop.stop()
B. XboxController.reset() + disconnect()
C. ConfigManager.flush()
D. LoggerFactory.shutdown()
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


class Application:
    """
    Top-level application orchestrator.

    Instantiates and wires all concrete subsystem components.
    Does NOT contain any business logic — pure composition root.

    Parameters
    ----------
    config_path:
        Optional override path to the user configuration TOML file.
    """

    def __init__(self, config_path: Path | None = None) -> None:
        # All subsystem references are stored as attributes for shutdown access.
        # They are populated in run() in strict startup-order.

        self._config_path = config_path

        # ── Subsystem handles (populated in run()) ─────────────────────────
        self._config_manager = None
        self._event_bus = None
        self._plugin_loader = None
        self._profile_manager = None
        self._capture_loop = None
        self._controller = None
        self._main_window = None

    def run(self) -> None:
        """
        Execute the full startup sequence and enter the UI event loop.

        This method blocks until the application is closed by the user.
        """
        raise NotImplementedError

    def _shutdown(self) -> None:
        """
        Perform a clean, ordered shutdown of all subsystems.

        Called when the UI window is closed or a shutdown signal is received.
        """
        raise NotImplementedError

    # ── Wiring helpers (called in order from run()) ────────────────────────

    def _configure_logging(self) -> None:
        """Step 1: Configure LoggerFactory from loaded LoggingConfig."""
        raise NotImplementedError

    def _load_config(self) -> None:
        """Step 2: Load and merge configuration files."""
        raise NotImplementedError

    def _create_event_bus(self) -> None:
        """Step 3: Instantiate the EventBus."""
        raise NotImplementedError

    def _run_health_check(self) -> None:
        """Step 4: Run pre-flight checks. Exit on critical failure."""
        raise NotImplementedError

    def _discover_plugins(self) -> None:
        """Step 5: Load and activate the configured game plugin."""
        raise NotImplementedError

    def _load_profile(self) -> None:
        """Step 6 & 7: Load user profile and calibration data."""
        raise NotImplementedError

    def _wire_pipeline(self) -> None:
        """Step 8 & 9: Construct and connect all pipeline components."""
        raise NotImplementedError

    def _build_ui(self) -> None:
        """Step 10: Construct the main window and all UI panels."""
        raise NotImplementedError

    def _start_capture(self) -> None:
        """Step 11: Start the CaptureLoop daemon thread."""
        raise NotImplementedError
