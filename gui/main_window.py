"""
gesturedrive.gui.main_window
============================
MainWindow: Master dashboard interface assembling Top Bar, Camera Preview, Telemetry Dashboard,
Status Bar, Control Panel, and Pipeline Worker thread.
"""

from __future__ import annotations

import logging
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QMainWindow,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from gui.calibration_dialog import CalibrationDialog
from gui.camera_widget import CameraWidget
from gui.control_panel import ControlPanelWidget
from gui.diagnostics_dialog import DiagnosticsDialog
from gui.profile_dialog import ProfileDialog
from gui.settings_dialog import SettingsDialog
from gui.status_bar import StatusBarWidget
from gui.styles import DARK_THEME_QSS
from gui.telemetry_panel import TelemetryPanel
from gui.top_bar import TopBarWidget
from gui.worker import PipelineWorker
from games.monitor import GameMonitor
from games.prefs import DetectionPrefs
from games.registry import GameRegistry
from desktop import AppMode, ModeManager
from profiles.profile_manager import ProfileManager

from core.resources import apply_app_icon
from core.version import get_window_title

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """
    Main Application Control Center Window.
    """

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle(get_window_title())
        apply_app_icon(self)
        self.resize(1400, 850)
        self.setMinimumSize(1280, 800)

        # Apply commercial dark theme QSS
        self.setStyleSheet(DARK_THEME_QSS)

        # Setup Native Menu Bar
        self._setup_menu_bar()

        # Central Widget & Root Layout
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(14)

        # 1. Top Bar
        self.top_bar = TopBarWidget()
        root_layout.addWidget(self.top_bar)

        # 2. Main Dashboard Area (Left Area ≈ 70%: Camera Preview, Right Area ≈ 30%: Telemetry Panel)
        dash_layout = QHBoxLayout()
        dash_layout.setSpacing(14)

        self.camera_widget = CameraWidget()
        self.telemetry_panel = TelemetryPanel()

        dash_layout.addWidget(self.camera_widget, stretch=7)
        dash_layout.addWidget(self.telemetry_panel, stretch=3)

        root_layout.addLayout(dash_layout, stretch=1)

        # 3. Bottom Status Bar
        self.status_bar_widget = StatusBarWidget()
        root_layout.addWidget(self.status_bar_widget)

        # 4. Bottom Control Panel
        self.control_panel = ControlPanelWidget()
        root_layout.addWidget(self.control_panel)

        # Worker Thread & Active Dialog handles
        self.worker: PipelineWorker | None = None
        self.active_calib_dialog: CalibrationDialog | None = None
        self.active_diag_dialog:  DiagnosticsDialog | None = None
        self.active_settings_dialog: SettingsDialog | None = None
        self.active_help_dialog = None

        # Mode Manager — init before GUI wiring so mode is ready at startup
        self.mode_manager = ModeManager(
            on_mode_changed=self._on_mode_changed,
        )

        # Profile Manager — init before GUI wiring so profiles are ready at startup
        self.profile_manager = ProfileManager(
            on_profile_changed=self._on_profile_changed,
        )
        self._init_profile_selector()

        # Game detection — prefs, registry, monitor
        self._detection_prefs = DetectionPrefs()
        self._game_registry   = GameRegistry()
        self._game_monitor    = GameMonitor(
            prefs=self._detection_prefs,
            registry=self._game_registry,
        )
        self._game_monitor.game_detected.connect(self._on_game_detected)
        self._game_monitor.game_exited.connect(self._on_game_exited)
        self._game_monitor.status_tick.connect(self._on_game_status_tick)
        self._game_monitor.start()   # lightweight — runs even before pipeline

        # Connect Control Panel signals
        self.control_panel.start_requested.connect(self.start_pipeline)
        self.control_panel.stop_requested.connect(self.stop_pipeline)
        self.control_panel.calibrate_requested.connect(self.open_calibration_wizard)
        self.control_panel.profiles_requested.connect(self.open_profile_manager)
        self.control_panel.settings_requested.connect(self.open_settings_window)
        self.control_panel.diagnostics_requested.connect(self.open_diagnostics_window)
        self.control_panel.exit_requested.connect(self.close)

        # Top bar profile, mode & help switches
        self.top_bar.profile_switch_requested.connect(self._on_profile_switch_requested)
        self.top_bar.mode_switch_requested.connect(self._on_mode_switch_requested)
        self.top_bar.help_requested.connect(self.open_help_center)
        self.top_bar.update_mode(self.mode_manager.active_mode.value)

    def _setup_menu_bar(self) -> None:
        """Create professional native Menu Bar with File, View, Tools, and Help menus."""
        menu_bar = self.menuBar()

        # 1. File Menu
        file_menu = menu_bar.addMenu("&File")

        act_new_profile = file_menu.addAction("➕  New Profile")
        act_new_profile.setShortcut("Ctrl+N")
        act_new_profile.triggered.connect(self._menu_new_profile)

        act_import_profile = file_menu.addAction("📥  Import Profile...")
        act_import_profile.setShortcut("Ctrl+I")
        act_import_profile.triggered.connect(self._menu_import_profile)

        act_export_profile = file_menu.addAction("📤  Export Active Profile...")
        act_export_profile.setShortcut("Ctrl+E")
        act_export_profile.triggered.connect(self._menu_export_profile)

        file_menu.addSeparator()

        act_exit = file_menu.addAction("🚪  Exit")
        act_exit.setShortcut("Alt+F4")
        act_exit.triggered.connect(self.close)

        # 2. View Menu
        view_menu = menu_bar.addMenu("&View")

        act_fullscreen = view_menu.addAction("🖥️  Toggle Full Screen")
        act_fullscreen.setShortcut("F11")
        act_fullscreen.triggered.connect(self._menu_toggle_fullscreen)

        act_toggle_telemetry = view_menu.addAction("📊  Toggle Telemetry Panel")
        act_toggle_telemetry.setShortcut("Ctrl+T")
        act_toggle_telemetry.triggered.connect(self._menu_toggle_telemetry)

        act_toggle_diag = view_menu.addAction("🔬  Toggle Diagnostics")
        act_toggle_diag.setShortcut("Ctrl+D")
        act_toggle_diag.triggered.connect(self.open_diagnostics_window)

        # 3. Tools Menu
        tools_menu = menu_bar.addMenu("&Tools")

        act_settings = tools_menu.addAction("⚙️  Settings...")
        act_settings.setShortcut("Ctrl+S")
        act_settings.triggered.connect(self.open_settings_window)

        act_calibrate = tools_menu.addAction("🎯  Calibration Wizard...")
        act_calibrate.setShortcut("Ctrl+K")
        act_calibrate.triggered.connect(self.open_calibration_wizard)

        act_profiles = tools_menu.addAction("📁  Profile Manager...")
        act_profiles.setShortcut("Ctrl+P")
        act_profiles.triggered.connect(self.open_profile_manager)

        act_diagnostics = tools_menu.addAction("🔬  Diagnostics Center...")
        act_diagnostics.triggered.connect(self.open_diagnostics_window)

        # 4. Help Menu
        help_menu = menu_bar.addMenu("&Help")

        act_docs = help_menu.addAction("📖  Documentation & Help Center")
        act_docs.setShortcut("F1")
        act_docs.triggered.connect(self.open_help_center)

        act_about = help_menu.addAction("ℹ️  About DriveByGesture")
        act_about.setShortcut("Shift+F1")
        act_about.triggered.connect(self._menu_about)

    def _menu_new_profile(self) -> None:
        name, ok = QInputDialog.getText(self, "New Profile", "Enter new profile name:")
        if ok and name.strip():
            try:
                p = self.profile_manager.create(name.strip())
                self.profile_manager.set_active(p.name)
                QMessageBox.information(self, "Profile Created", f"Profile '{p.name}' created and set active.")
            except Exception as exc:
                QMessageBox.warning(self, "Creation Error", f"Could not create profile: {exc}")

    def _menu_import_profile(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "Import Profile", "", "JSON Files (*.json)")
        if file_path:
            try:
                p = self.profile_manager.import_profile(file_path)
                self.profile_manager.set_active(p.name)
                QMessageBox.information(self, "Import Successful", f"Imported and activated profile '{p.name}'.")
            except Exception as exc:
                QMessageBox.warning(self, "Import Error", f"Failed to import profile: {exc}")

    def _menu_export_profile(self) -> None:
        active_name = self.profile_manager.active_name
        dest_path, _ = QFileDialog.getSaveFileName(self, "Export Active Profile", f"{active_name}.json", "JSON Files (*.json)")
        if dest_path:
            try:
                self.profile_manager.export_profile(active_name, dest_path)
                QMessageBox.information(self, "Export Successful", f"Exported profile '{active_name}' to:\n{dest_path}")
            except Exception as exc:
                QMessageBox.warning(self, "Export Error", f"Failed to export profile: {exc}")

    def _menu_toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def _menu_toggle_telemetry(self) -> None:
        self.telemetry_panel.setVisible(not self.telemetry_panel.isVisible())

    def _menu_about(self) -> None:
        dialog = self.open_settings_window()
        if dialog and hasattr(dialog, "nav_list"):
            dialog.nav_list.setCurrentRow(6)

    def start_pipeline(self) -> None:
        """Start the background backend pipeline worker thread."""
        if self.worker is not None and self.worker.isRunning():
            return

        logger.info("Starting backend pipeline thread...")
        self.top_bar.update_status("Starting...", "#ffb300")
        self.control_panel.set_pipeline_running(True)

        self.worker = PipelineWorker()
        self.worker.mode_manager = self.mode_manager
        active_p = getattr(self.profile_manager, "active_profile", None) or getattr(self.profile_manager, "active", None)
        if active_p and hasattr(self.worker, "configure_from_profile"):
            self.worker.configure_from_profile(active_p)
            if hasattr(active_p, "desktop") and isinstance(active_p.desktop, dict):
                self.mode_manager.set_mode(active_p.desktop.get("mode", self.mode_manager.active_mode.value))
        self.worker.frame_processed.connect(self._on_frame_processed)
        self.worker.status_changed.connect(self._on_status_changed)
        self.worker.error_occurred.connect(self._on_error_occurred)
        self.worker.finished.connect(self._on_worker_finished)

        self.worker.start()

    def stop_pipeline(self) -> None:
        """Stop the running backend pipeline worker thread safely."""
        if self.worker is not None and self.worker.isRunning():
            logger.info("Stopping backend pipeline thread...")
            self.top_bar.update_status("Stopping...", "#ffb300")
            self.worker.stop()
            self.worker.wait(3000)

        self._on_worker_finished()

    # ── Profile Manager ────────────────────────────────────────────────────────

    def _init_profile_selector(self) -> None:
        """Populate top-bar profile selector from ProfileManager."""
        names = self.profile_manager.list_names()
        self.top_bar.profile_selector.set_profiles(names)
        self.top_bar.profile_selector.set_active_profile(self.profile_manager.active_name)

    def open_profile_manager(self) -> None:
        """Open the Profile Manager dialog."""
        dialog = ProfileDialog(
            profile_manager=self.profile_manager,
            active_name=self.profile_manager.active_name,
            parent=self,
        )
        dialog.profile_activated.connect(self._on_profile_switch_requested)
        dialog.exec()
        # Refresh selector after any CRUD operations
        self._init_profile_selector()

    def _on_profile_switch_requested(self, name: str) -> None:
        """Switch to the requested profile, reload calibration, and update UI."""
        if name == self.profile_manager.active_name:
            return
        try:
            profile = self.profile_manager.set_active(name)
            self._apply_profile_to_pipeline(profile)
            logger.info("MainWindow: switched to profile '%s'.", name)
        except FileNotFoundError as exc:
            QMessageBox.warning(self, "Profile Switch Failed", str(exc))

    def _on_mode_switch_requested(self, mode_str: str) -> None:
        """Switch application mode live from top-bar selector."""
        self.mode_manager.set_mode(mode_str)

    def _on_mode_changed(self, mode: AppMode) -> None:
        """Called when ModeManager active mode changes."""
        self.top_bar.update_mode(mode.value)
        if self.worker and hasattr(self.worker, "mode_manager"):
            self.worker.mode_manager = self.mode_manager
        logger.info("MainWindow: operating mode set to '%s'.", mode.value)

    def _on_profile_changed(self, profile) -> None:
        """Called by ProfileManager when active profile changes."""
        self.top_bar.profile_selector.set_active_profile(profile.name)
        self._init_profile_selector()
        self._apply_profile_to_pipeline(profile)

        # Refresh active SettingsDialog pages if open
        dialog = self.active_settings_dialog
        if dialog and dialog.isVisible():
            if hasattr(dialog, "page_desktop") and hasattr(dialog.page_desktop, "set_config"):
                dialog.page_desktop.set_config(getattr(profile, "desktop", {}))
            if hasattr(dialog, "page_camera") and hasattr(dialog.page_camera, "set_config"):
                dialog.page_camera.set_config(getattr(profile, "camera", {}))
            if hasattr(dialog, "page_steering") and hasattr(dialog.page_steering, "set_config"):
                dialog.page_steering.set_config(getattr(profile, "steering", {}))
            if hasattr(dialog, "page_controller") and hasattr(dialog.page_controller, "set_config"):
                dialog.page_controller.set_config(getattr(profile, "controller", {}))
            if hasattr(dialog, "page_general") and hasattr(dialog.page_general, "set_config"):
                dialog.page_general.set_config(profile)
            if hasattr(dialog, "page_profiles") and hasattr(dialog.page_profiles, "refresh_profiles"):
                dialog.page_profiles.refresh_profiles()
            if hasattr(dialog, "page_calibration") and hasattr(dialog.page_calibration, "update_status"):
                dialog.page_calibration.update_status()

        logger.info("MainWindow: profile changed to '%s' and synchronized live.", profile.name)

    def _apply_profile_to_pipeline(self, profile) -> None:
        """
        Apply a newly-activated profile to the live pipeline.

        Loads embedded calibration data into CalibrationManager and desktop settings into DesktopController.
        If the pipeline is not running, configuration is applied on next start.
        """
        if self.worker and hasattr(self.worker, "apply_profile"):
            self.worker.apply_profile(profile)
        elif hasattr(profile, "desktop") and isinstance(profile.desktop, dict):
            desk_cfg = profile.desktop
            if self.worker and hasattr(self.worker, "desktop_controller") and self.worker.desktop_controller:
                self.worker.desktop_controller.apply_config(desk_cfg)
            if "mode" in desk_cfg:
                self.mode_manager.set_mode(desk_cfg["mode"])

        if self.worker is None or self.worker.calibration_manager is None:
            return
        cal_data = profile.get_calibration_data()
        if cal_data is not None:
            try:
                self.worker.calibration_manager.save_calibration(cal_data)
                self.status_bar_widget.set_component_status("Calibration", "Loaded", "good")
                logger.info("MainWindow: applied profile calibration to live pipeline.")
            except Exception as exc:
                logger.warning("MainWindow: could not apply profile calibration: %s", exc)
        else:
            logger.info("MainWindow: profile '%s' has no calibration — using current.", profile.name)

    # ── Calibration accepted hook ──────────────────────────────────────────────

    def _on_calibration_accepted(self) -> None:
        """After calibration wizard succeeds, embed new data into active profile."""
        if self.worker and self.worker.calibration_manager:
            cal_data = self.worker.calibration_manager.active_calibration
            if cal_data:
                self.profile_manager.update_calibration(cal_data)

    def open_calibration_wizard(self) -> None:
        """Launch graphical Calibration Wizard dialog."""
        if self.worker is None or not self.worker.isRunning():
            self.start_pipeline()
            # Brief wait for worker initialization
            QApplication.processEvents()

        if self.worker is None or self.worker.calibration_manager is None:
            QMessageBox.warning(self, "Calibration Error", "Pipeline worker is not initialized.")
            return

        logger.info("Opening Calibration Wizard dialog...")
        dialog = CalibrationDialog(self.worker.calibration_manager, self)
        self.active_calib_dialog = dialog
        result = dialog.exec()
        self.active_calib_dialog = None

        if result == CalibrationDialog.DialogCode.Accepted:
            self.status_bar_widget.set_component_status("Calibration", "Loaded", "good")
            self._on_calibration_accepted()

    def open_settings_window(self) -> None:
        """Launch graphical Settings & Configuration dialog."""
        if self.worker is None or not self.worker.isRunning():
            self.start_pipeline()
            QApplication.processEvents()

        if self.worker is None or self.worker.calibration_manager is None:
            QMessageBox.warning(self, "Settings Error", "Pipeline worker is not initialized.")
            return

        logger.info("Opening Settings dialog...")
        dialog = SettingsDialog(self.worker.calibration_manager, self)
        self.active_settings_dialog = dialog
        dialog.config_applied.connect(self._on_live_config_applied)
        dialog.open_wizard_requested.connect(self.open_calibration_wizard)
        dialog.reconnect_controller_requested.connect(self._on_reconnect_controller)

        active_p = getattr(self.profile_manager, "active_profile", None) or getattr(self.profile_manager, "active", None)
        if active_p:
            if hasattr(dialog, "page_desktop") and hasattr(dialog.page_desktop, "set_config"):
                dialog.page_desktop.set_config(getattr(active_p, "desktop", {}))
            if hasattr(dialog, "page_camera") and hasattr(dialog.page_camera, "set_config"):
                dialog.page_camera.set_config(getattr(active_p, "camera", {}))
            if hasattr(dialog, "page_steering") and hasattr(dialog.page_steering, "set_config"):
                dialog.page_steering.set_config(getattr(active_p, "steering", {}))
            if hasattr(dialog, "page_controller") and hasattr(dialog.page_controller, "set_config"):
                dialog.page_controller.set_config(getattr(active_p, "controller", {}))
            if hasattr(dialog, "page_general") and hasattr(dialog.page_general, "set_config"):
                dialog.page_general.set_config(active_p)
            if hasattr(dialog, "page_profiles") and hasattr(dialog.page_profiles, "set_profile_manager"):
                dialog.page_profiles.set_profile_manager(self.profile_manager)
            if hasattr(dialog, "page_calibration") and hasattr(dialog.page_calibration, "update_status"):
                dialog.page_calibration.update_status()

        dialog.exec()
        self.active_settings_dialog = None

    def _on_reconnect_controller(self) -> None:
        """Reconnect virtual controller output backend."""
        if self.worker is not None:
            active_p = getattr(self.profile_manager, "active_profile", None) or getattr(self.profile_manager, "active", None)
            ctrl_cfg = getattr(active_p, "controller", None) if active_p else None
            self.worker.apply_controller_config(ctrl_cfg)
            QMessageBox.information(self, "Controller Reconnect", "Virtual Xbox Controller backend reconnected.")

    def open_diagnostics_window(self) -> None:
        """Open or bring to front the non-modal Diagnostics window."""
        if self.active_diag_dialog is not None and self.active_diag_dialog.isVisible():
            self.active_diag_dialog.raise_()
            self.active_diag_dialog.activateWindow()
            return

        logger.info("Opening Diagnostics window...")
        dialog = DiagnosticsDialog(worker=self.worker, parent=self)
        self.active_diag_dialog = dialog
        dialog.finished.connect(self._on_diagnostics_closed)
        dialog.show()

    def open_help_center(self) -> None:
        """Open or bring to front the non-modal Help & Documentation Center."""
        if hasattr(self, "active_help_dialog") and self.active_help_dialog is not None and self.active_help_dialog.isVisible():
            self.active_help_dialog.raise_()
            self.active_help_dialog.activateWindow()
            return

        from gui.help_dialog import HelpCenterDialog
        logger.info("Opening Help & Documentation Center...")
        dialog = HelpCenterDialog(self)
        self.active_help_dialog = dialog
        dialog.show()

    def _on_live_config_applied(self, camera_config, steering_config) -> None:
        """Apply live configuration changes defensively to UI and worker pipeline thread."""
        try:
            if camera_config and hasattr(camera_config, "mirror_preview"):
                self.camera_widget.mirror_preview = getattr(camera_config, "mirror_preview", True)
            if camera_config and hasattr(camera_config, "overlay_enabled"):
                self.camera_widget.overlay_enabled = getattr(camera_config, "overlay_enabled", True)

            if self.worker:
                self.worker.apply_live_config(camera_config, steering_config)
                logger.info("Live configuration updated on MainWindow.")
        except Exception as exc:
            logger.warning("MainWindow live configuration update skipped safely: %s", exc)

    def _on_frame_processed(self, frame: np.ndarray, fps: float, telemetry: dict) -> None:
        """Handle incoming processed video frame and live telemetry metrics."""
        self.camera_widget.update_frame(frame, overlay_info=telemetry)
        self.top_bar.update_fps(fps)
        self.top_bar.update_status("Running", "#00e676")
        self.top_bar.update_info(
            profile_name=telemetry.get("profile_name"),
            camera_name=telemetry.get("camera_name"),
        )
        self.telemetry_panel.update_telemetry_data(telemetry)

        # Forward telemetry to Diagnostics window if open
        if self.active_diag_dialog is not None and self.active_diag_dialog.isVisible():
            self.active_diag_dialog.update_telemetry(telemetry)

        # Forward telemetry to Settings window if open
        if self.active_settings_dialog is not None and self.active_settings_dialog.isVisible():
            self.active_settings_dialog.update_telemetry(telemetry)

        # Route calibration frame and snapshot to active dialog if open
        if self.active_calib_dialog is not None and self.active_calib_dialog.isVisible():
            snap = telemetry.get("calibration_snapshot")
            self.active_calib_dialog.update_telemetry_frame(frame, snap)

    def _on_status_changed(self, component: str, status_str: str, state: str) -> None:
        """Update status bar indicators and forward to diagnostics window."""
        self.status_bar_widget.set_component_status(component, status_str, state)
        if self.active_diag_dialog is not None and self.active_diag_dialog.isVisible():
            self.active_diag_dialog.on_status_changed(component, status_str, state)

    def _on_error_occurred(self, title: str, message: str) -> None:
        """Handle backend runtime error dialog without crashing the GUI."""
        logger.error("GUI Error Event: %s — %s", title, message)
        self.camera_widget.show_error_banner(title)
        QMessageBox.warning(self, title, message)

    def _on_worker_finished(self) -> None:
        """Called when worker thread stops or terminates."""
        self.control_panel.set_pipeline_running(False)
        self.top_bar.update_status("Stopped", "#8f96a3")
        self.top_bar.update_fps(0.0)
        self.camera_widget.show_offline_banner("Camera Offline")

    def _on_diagnostics_closed(self) -> None:
        """Clear diagnostics dialog reference when closed."""
        self.active_diag_dialog = None
        logger.info("Diagnostics window closed.")

    # ── Game Detection handlers ───────────────────────────────────────────

    def _on_game_detected(self, preset) -> None:
        """
        Called on the GUI thread when GameMonitor detects a running game.

        Decision tree:
        1. Detection disabled in prefs → do nothing.
        2. Game is in ignored list → do nothing.
        3. Game is in always-switch list → switch silently.
        4. Matching profile exists → prompt user (Switch / Ignore / Always / Never).
        5. No matching profile → offer to create one from preset.
        """
        if not self._detection_prefs.enabled:
            return

        game_id = preset.game_id
        suggested = preset.suggested_profile_name

        # Step 1: Check ignore list
        if self._detection_prefs.is_ignored(game_id):
            logger.debug("GameDetection: '%s' is ignored, skipping.", game_id)
            return

        # Step 2: Check always-switch list
        if self._detection_prefs.is_always_switch(game_id):
            if suggested in self.profile_manager.list_names():
                self._switch_profile_for_game(preset)
            return

        # Step 3: Already on the right profile — no prompt needed
        if self.profile_manager.active_name == suggested:
            return

        # Step 4: Matching profile exists → prompt
        if suggested in self.profile_manager.list_names():
            self._prompt_profile_switch(preset)
        else:
            # Step 5: No profile → offer to create one
            self._prompt_create_profile(preset)

    def _on_game_exited(self) -> None:
        """Called when the previously detected game is no longer running."""
        self.telemetry_panel.update_game_status("")
        self.status_bar_widget.update_game_chip("")
        logger.info("GameDetection: game exited, dashboard updated.")

    def _on_game_status_tick(self, game_name: str) -> None:
        """Called every poll cycle. Updates dashboard game card (not profile switch logic)."""
        self.telemetry_panel.update_game_status(game_name)
        self.status_bar_widget.update_game_chip(game_name)

    def _prompt_profile_switch(self, preset) -> None:
        """Show a non-blocking info dialog prompting the user to switch profiles."""
        from PySide6.QtWidgets import QPushButton  # noqa: PLC0415
        msg = QMessageBox(self)
        msg.setWindowTitle("Game Detected")
        msg.setText(
            f"<b>{preset.display_name}</b> detected.<br><br>"
            f"Switch to the <b>{preset.suggested_profile_name}</b> profile?"
        )
        msg.setIcon(QMessageBox.Information)

        btn_switch  = msg.addButton("Switch", QMessageBox.AcceptRole)
        btn_always  = msg.addButton("Always Switch", QMessageBox.YesRole)
        btn_never   = msg.addButton("Never Ask", QMessageBox.NoRole)
        btn_ignore  = msg.addButton("Ignore", QMessageBox.RejectRole)

        msg.exec()
        clicked = msg.clickedButton()

        if clicked is btn_switch:
            self._switch_profile_for_game(preset)
        elif clicked is btn_always:
            self._detection_prefs.set_always_switch(preset.game_id)
            self._switch_profile_for_game(preset)
        elif clicked is btn_never:
            self._detection_prefs.set_ignored(preset.game_id)
        # btn_ignore: do nothing, do not save preference

    def _prompt_create_profile(self, preset) -> None:
        """Offer to create a new profile from the game's preset settings."""
        reply = QMessageBox.question(
            self,
            "Create Game Profile?",
            f"<b>{preset.display_name}</b> detected, but no matching profile was found.<br><br>"
            f"Create a new profile <b>'{preset.suggested_profile_name}'</b> "
            f"with recommended settings for this game?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        try:
            profile = self.profile_manager.create(
                name=preset.suggested_profile_name,
                description=preset.description,
                game_name=preset.display_name,
            )
            # Apply preset steering settings
            profile.steering.update(preset.default_steering)
            profile.metadata.touch()
            self.profile_manager.save_active()
            self._init_profile_selector()
            # Immediately activate the new profile
            self._switch_profile_for_game(preset)
        except ValueError as exc:
            QMessageBox.warning(self, "Create Profile Failed", str(exc))

    def _switch_profile_for_game(self, preset) -> None:
        """Silently switch to the suggested profile for a detected game."""
        name = preset.suggested_profile_name
        if name not in self.profile_manager.list_names():
            return
        try:
            profile = self.profile_manager.set_active(name)
            self._apply_profile_to_pipeline(profile)
            self._init_profile_selector()
            logger.info("GameDetection: switched to profile '%s' for '%s'.",
                        name, preset.display_name)
        except Exception as exc:
            logger.warning("GameDetection: profile switch failed: %s", exc)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Ensure clean shutdown of pipeline worker, save active profile, and release resources."""
        logger.info("Window close requested. Performing graceful shutdown...")
        try:
            self.profile_manager.save_active()
        except Exception as exc:
            logger.warning("MainWindow: could not save active profile on close: %s", exc)
        # Stop game monitor
        if self._game_monitor.isRunning():
            self._game_monitor.stop()
            self._game_monitor.wait(2000)
        if self.worker is not None and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(2000)
        event.accept()
