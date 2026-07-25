"""
gesturedrive.gui.styles
=======================
Styles, color tokens, and QSS dark theme for DriveByGesture PySide6 desktop interface.
"""

from __future__ import annotations

# Color Palette Constants
COLOR_BG_DARK = "#101014"
COLOR_BG_CARD = "#1a1a22"
COLOR_BG_PANEL = "#16161e"
COLOR_BORDER = "#2e2e3e"
COLOR_TEXT_PRIMARY = "#ffffff"
COLOR_TEXT_SECONDARY = "#a0a0b8"
COLOR_TEXT_MUTED = "#6c6c84"

# Accent Colors
COLOR_ACCENT_CYAN = "#00e5ff"
COLOR_ACCENT_GREEN = "#00e676"
COLOR_ACCENT_RED = "#ff1744"
COLOR_ACCENT_AMBER = "#ffb300"
COLOR_ACCENT_BLUE = "#2979ff"

DARK_THEME_QSS = """
QMainWindow {
    background-color: #101014;
    color: #ffffff;
}

QWidget {
    font-family: "Segoe UI", -apple-system, Roboto, Helvetica, sans-serif;
    font-size: 13px;
    color: #ffffff;
}

/* Card / Container Panels */
QFrame#topBar, QFrame#cameraCard, QFrame#telemetryCard, QFrame#statusBar, QFrame#controlPanel {
    background-color: #181820;
    border: 1px solid #2a2a3a;
    border-radius: 10px;
}

QFrame#statusCard {
    background-color: #1f1f2a;
    border: 1px solid #2e2e40;
    border-radius: 8px;
}

/* Typography & Titles */
QLabel#appTitle {
    font-size: 20px;
    font-weight: bold;
    color: #00e5ff;
    letter-spacing: 1px;
}

QLabel#sectionTitle {
    font-size: 14px;
    font-weight: 600;
    color: #a0a0b8;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

QLabel#telemetryValue {
    font-size: 22px;
    font-weight: bold;
    color: #00e5ff;
}

QLabel#telemetryLabel {
    font-size: 12px;
    color: #a0a0b8;
}

/* Buttons */
QPushButton {
    background-color: #242432;
    color: #ffffff;
    border: 1px solid #38384d;
    border-radius: 8px;
    padding: 10px 20px;
    font-size: 13px;
    font-weight: 600;
    min-width: 100px;
}

QPushButton:hover {
    background-color: #2e2e42;
    border-color: #00e5ff;
    color: #00e5ff;
}

QPushButton:pressed {
    background-color: #1a1a26;
}

QPushButton:disabled {
    background-color: #161620;
    color: #4a4a60;
    border-color: #222230;
}

/* Special Button Variants */
QPushButton#btnStart {
    background-color: #00897b;
    border-color: #00bfa5;
    color: #ffffff;
}

QPushButton#btnStart:hover {
    background-color: #00bfa5;
    border-color: #64ffda;
}

QPushButton#btnStop {
    background-color: #c62828;
    border-color: #e53935;
    color: #ffffff;
}

QPushButton#btnStop:hover {
    background-color: #e53935;
    border-color: #ff5252;
}

QPushButton#btnExit {
    background-color: #37474f;
    border-color: #546e7a;
    color: #eceff1;
}

QPushButton#btnExit:hover {
    background-color: #455a64;
    border-color: #90a4ae;
}

/* Status Bar & Indicators */
QLabel#statusIndicator {
    font-weight: bold;
    font-size: 12px;
    padding: 3px 8px;
    border-radius: 4px;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background: #14141c;
    width: 8px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background: #2e2e40;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #00e5ff;
}
"""
