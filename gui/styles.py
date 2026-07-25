"""
gesturedrive.gui.styles
=======================
Styles, color tokens, and QSS dark theme for DriveByGesture PySide6 desktop interface.
Inspired by commercial software (Logitech G Hub, OBS Studio, SimHub).
"""

from __future__ import annotations

# Color Palette Tokens
COLOR_BG_DARK = "#0d0e12"
COLOR_BG_PANEL = "#14161f"
COLOR_BG_CARD = "#1a1d28"
COLOR_BG_CARD_HOVER = "#202432"
COLOR_BORDER = "#282c3c"

# Typography Colors
COLOR_TEXT_PRIMARY = "#ffffff"
COLOR_TEXT_SECONDARY = "#8f96a3"
COLOR_TEXT_MUTED = "#5b616e"

# Accent Colors
COLOR_ACCENT_CYAN = "#00e5ff"
COLOR_ACCENT_GREEN = "#00e676"
COLOR_ACCENT_RED = "#ff1744"
COLOR_ACCENT_AMBER = "#ffb300"
COLOR_ACCENT_BLUE = "#2979ff"

DARK_THEME_QSS = """
QMainWindow {
    background-color: #0d0e12;
    color: #ffffff;
}

QWidget {
    font-family: "Segoe UI", -apple-system, Roboto, Helvetica, sans-serif;
    font-size: 13px;
    color: #ffffff;
}

/* Card Containers & Panels */
QFrame#topBar, QFrame#cameraCard, QFrame#telemetryCard, QFrame#statusBar, QFrame#controlPanel {
    background-color: #14161f;
    border: 1px solid #282c3c;
    border-radius: 10px;
}

QFrame#statusCard {
    background-color: #1a1d28;
    border: 1px solid #282c3c;
    border-radius: 10px;
}

QFrame#statusCard:hover {
    border-color: #363b50;
    background-color: #1c202d;
}

/* Typography & Titles */
QLabel#appTitle {
    font-size: 22px;
    font-weight: 800;
    color: #00e5ff;
    letter-spacing: 1.5px;
}

QLabel#sectionTitle {
    font-size: 13px;
    font-weight: 700;
    color: #8f96a3;
    letter-spacing: 1px;
}

QLabel#telemetryLabel {
    font-size: 11px;
    font-weight: 600;
    color: #8f96a3;
    text-transform: uppercase;
}

QLabel#telemetryValue {
    font-size: 18px;
    font-weight: 700;
    color: #00e5ff;
}

/* Pill Badges & Chips */
QLabel#pillBadge {
    background-color: #11131a;
    color: #8f96a3;
    font-size: 12px;
    font-weight: 600;
    padding: 5px 12px;
    border-radius: 14px;
    border: 1px solid #282c3c;
}

QLabel#statusChip {
    background-color: #11131a;
    color: #ffffff;
    font-size: 12px;
    font-weight: 600;
    padding: 6px 14px;
    border-radius: 14px;
    border: 1px solid #282c3c;
}

/* Buttons */
QPushButton {
    background-color: #202434;
    color: #ffffff;
    border: 1px solid #32384e;
    border-radius: 8px;
    padding: 0px 18px;
    height: 40px;
    min-height: 40px;
    font-size: 13px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #2a3044;
    border-color: #00e5ff;
    color: #00e5ff;
}

QPushButton:pressed {
    background-color: #181b28;
}

QPushButton:disabled {
    background-color: #141620;
    color: #484e5e;
    border-color: #222634;
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
    color: #ffffff;
}

QPushButton#btnStop {
    background-color: #c62828;
    border-color: #e53935;
    color: #ffffff;
}

QPushButton#btnStop:hover {
    background-color: #e53935;
    border-color: #ff5252;
    color: #ffffff;
}

QPushButton#btnExit {
    background-color: #2c343a;
    border-color: #455a64;
    color: #eceff1;
}

QPushButton#btnExit:hover {
    background-color: #37474f;
    border-color: #78909c;
    color: #ffffff;
}

/* QProgressBar Styling */
QProgressBar {
    background-color: #11131a;
    border: 1px solid #282c3c;
    border-radius: 5px;
    text-align: center;
    color: #ffffff;
    font-size: 11px;
    font-weight: 600;
    height: 12px;
}

QProgressBar::chunk {
    background-color: #00e5ff;
    border-radius: 4px;
}

QProgressBar#pbTriggerRT::chunk {
    background-color: #00e676;
}

QProgressBar#pbTriggerLT::chunk {
    background-color: #ff1744;
}

QProgressBar#pbConfidence::chunk {
    background-color: #00e5ff;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background: #0d0e12;
    width: 6px;
    border-radius: 3px;
}

QScrollBar::handle:vertical {
    background: #282c3c;
    border-radius: 3px;
}

QScrollBar::handle:vertical:hover {
    background: #00e5ff;
}

QScrollArea {
    border: none;
    background: transparent;
}
"""
