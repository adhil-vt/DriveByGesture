"""
gesturedrive.gui.styles
=======================
Styles, color tokens, and master QSS dark theme for DriveByGesture PySide6 desktop interface.
Designed to feel comparable to Logitech G Hub, SteelSeries GG, NVIDIA App, and Discord Desktop.
"""

from __future__ import annotations

# ── Color Palette Tokens ──────────────────────────────────────────────────────
COLOR_BG_DARK = "#0b0e14"
COLOR_BG_PANEL = "#121620"
COLOR_BG_CARD = "#1a1f2c"
COLOR_BG_CARD_HOVER = "#222838"
COLOR_BORDER = "#242a3c"

# ── Typography Colors ─────────────────────────────────────────────────────────
COLOR_TEXT_PRIMARY = "#ffffff"
COLOR_TEXT_SECONDARY = "#8f96a3"
COLOR_TEXT_MUTED = "#5b616e"

# ── Accent Colors ─────────────────────────────────────────────────────────────
COLOR_ACCENT_CYAN = "#00e5ff"
COLOR_ACCENT_GREEN = "#00e676"
COLOR_ACCENT_RED = "#ff5252"
COLOR_ACCENT_AMBER = "#ffb300"
COLOR_ACCENT_BLUE = "#2979ff"

DARK_THEME_QSS = """
QMainWindow {
    background-color: #0b0e14;
    color: #ffffff;
}

QWidget {
    font-family: "Segoe UI", -apple-system, Roboto, Helvetica, sans-serif;
    font-size: 13px;
    color: #ffffff;
}

/* ── Menu Bar & Context Menus ────────────────────────────────────────────── */
QMenuBar {
    background-color: #0b0e14;
    color: #8f96a3;
    border-bottom: 1px solid #1a1f2c;
    padding: 2px 8px;
    font-size: 12px;
    font-weight: 600;
}

QMenuBar::item {
    background: transparent;
    padding: 6px 10px;
    border-radius: 4px;
}

QMenuBar::item:selected {
    background-color: #1a1f2c;
    color: #00e5ff;
}

QMenu {
    background-color: #121620;
    border: 1px solid #242a3c;
    border-radius: 8px;
    padding: 6px;
}

QMenu::item {
    padding: 6px 24px 6px 12px;
    border-radius: 4px;
    color: #e0e6ed;
    font-size: 12px;
    font-weight: 500;
}

QMenu::item:selected {
    background-color: #1a1f2c;
    color: #00e5ff;
}

QMenu::separator {
    height: 1px;
    background-color: #242a3c;
    margin: 4px 8px;
}

/* ── Card Containers & Panels ────────────────────────────────────────────── */
QFrame#topBar, QFrame#cameraCard, QFrame#telemetryCard, QFrame#statusBar, QFrame#controlPanel {
    background-color: #121620;
    border: 1px solid #242a3c;
    border-radius: 10px;
}

QFrame#statusCard {
    background-color: #1a1f2c;
    border: 1px solid #242a3c;
    border-radius: 10px;
}

QFrame#statusCard:hover {
    border-color: #363b50;
    background-color: #222838;
}

/* ── Typography & Titles ─────────────────────────────────────────────────── */
QLabel#appTitle {
    font-size: 20px;
    font-weight: 800;
    color: #00e5ff;
    letter-spacing: 1.5px;
}

QLabel#sectionTitle {
    font-size: 12px;
    font-weight: 700;
    color: #8f96a3;
    letter-spacing: 1px;
    text-transform: uppercase;
}

QLabel#telemetryLabel {
    font-size: 11px;
    font-weight: 600;
    color: #8f96a3;
    text-transform: uppercase;
}

QLabel#telemetryValue {
    font-size: 16px;
    font-weight: 700;
    color: #00e5ff;
    font-family: 'Consolas', 'Courier New', monospace;
}

QLabel#monoValue {
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 13px;
    font-weight: 700;
    color: #00e5ff;
}

/* ── Pill Badges & Chips ─────────────────────────────────────────────────── */
QLabel#pillBadge {
    background-color: #0b0e14;
    color: #8f96a3;
    font-size: 12px;
    font-weight: 600;
    padding: 5px 14px;
    border-radius: 14px;
    border: 1px solid #242a3c;
}

QLabel#statusChip {
    background-color: #0b0e14;
    color: #ffffff;
    font-size: 12px;
    font-weight: 600;
    padding: 6px 14px;
    border-radius: 14px;
    border: 1px solid #242a3c;
}

/* ── Buttons ─────────────────────────────────────────────────────────────── */
QPushButton {
    background-color: #1a1f2c;
    color: #ffffff;
    border: 1px solid #242a3c;
    border-radius: 8px;
    padding: 0px 16px;
    height: 38px;
    min-height: 38px;
    font-size: 13px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #222838;
    border-color: #00e5ff;
    color: #00e5ff;
}

QPushButton:pressed {
    background-color: #141722;
}

QPushButton:disabled {
    background-color: #121620;
    color: #484e5e;
    border-color: #1c202d;
}

/* Primary Cyan Action Button */
QPushButton#btnStart {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00897b, stop:1 #00bfa5);
    border: 1px solid #00bfa5;
    color: #ffffff;
    font-weight: 700;
}

QPushButton#btnStart:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00bfa5, stop:1 #64ffda);
    border-color: #64ffda;
    color: #000000;
}

/* Stop Button */
QPushButton#btnStop {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #c62828, stop:1 #e53935);
    border: 1px solid #e53935;
    color: #ffffff;
    font-weight: 700;
}

QPushButton#btnStop:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #e53935, stop:1 #ff5252);
    border-color: #ff5252;
}

QPushButton#btnExit {
    background-color: #1c202d;
    border-color: #2e354a;
    color: #8f96a3;
}

QPushButton#btnExit:hover {
    background-color: #282e42;
    border-color: #ff5252;
    color: #ff5252;
}

/* ── Form Controls & Inputs ──────────────────────────────────────────────── */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #1a1f2c;
    color: #ffffff;
    border: 1px solid #242a3c;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 13px;
}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border-color: #00e5ff;
}

QComboBox::drop-down {
    border: none;
    padding-right: 10px;
}

QComboBox QAbstractItemView {
    background-color: #121620;
    border: 1px solid #242a3c;
    selection-background-color: #1a1f2c;
    selection-color: #00e5ff;
    padding: 4px;
}

/* ── Progress Bars ───────────────────────────────────────────────────────── */
QProgressBar {
    background-color: #0b0e14;
    border: 1px solid #242a3c;
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
    background-color: #ff5252;
}

QProgressBar#pbConfidence::chunk {
    background-color: #00e5ff;
}

/* ── Scrollbars & ScrollArea ─────────────────────────────────────────────── */
QScrollBar:vertical {
    border: none;
    background: #0b0e14;
    width: 6px;
    border-radius: 3px;
}

QScrollBar::handle:vertical {
    background: #242a3c;
    border-radius: 3px;
}

QScrollBar::handle:vertical:hover {
    background: #00e5ff;
}

QScrollBar:horizontal {
    border: none;
    background: #0b0e14;
    height: 6px;
    border-radius: 3px;
}

QScrollBar::handle:horizontal {
    background: #242a3c;
    border-radius: 3px;
}

QScrollBar::handle:horizontal:hover {
    background: #00e5ff;
}

QScrollArea {
    border: none;
    background: transparent;
}
"""
