"""
gesturedrive.app
=================
DriveByGesture Desktop GUI Application Entry Point (PySide6).
"""

from __future__ import annotations

import logging
import sys

from PySide6.QtWidgets import QApplication

from gui.logger import GUILogHandler
from gui.main_window import MainWindow

# Configure application logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

gui_handler = GUILogHandler(logging.INFO)
logger.addHandler(gui_handler)

console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(name)s: %(message)s", "%H:%M:%S"))
logger.addHandler(console_handler)


def main() -> int:
    """
    Main entry point for launching the DriveByGesture PySide6 Desktop GUI application.
    """
    app = QApplication(sys.argv)
    app.setApplicationName("DriveByGesture")
    app.setOrganizationName("GestureDrive")

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
