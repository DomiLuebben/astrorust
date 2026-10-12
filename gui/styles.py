# -*- coding: utf-8 -*-
"""
Theme-Definitionen für Astrorust.
Angelehnt an das KDE-Breeze-Dark Design des Linux Media Encoders (LME).
Kompakt, professionell, strukturiert mit Breeze-Blau (#3daee9) als Akzent.
"""

WINDOW = "#1a1d20"
SURFACE = "#232629"
SURFACE_RAISED = "#2a2e32"
SURFACE_SUNKEN = "#1c1f22"
BORDER = "#3a3f44"
BORDER_SOFT = "#31363b"
TEXT = "#eff0f1"
TEXT_MUTED = "#bdc3c7"
TEXT_DISABLED = "#70777d"
ACCENT = "#3daee9"
ACCENT_HOVER = "#5cc1f2"
ACCENT_DARK = "#2980b9"
START_GREEN = "#27ae60"
START_GREEN_HOVER = "#2ecc71"
STOP_RED = "#da4453"
STOP_RED_HOVER = "#ed5565"
WARN_ORANGE = "#f67400"

# Astrologische Farb-Tokens
COLOR_FIRE = "#f87171"
COLOR_EARTH = "#4ade80"
COLOR_AIR = "#fbbf24"
COLOR_WATER = "#60a5fa"

DARK_STYLESHEET = f"""
/* Globale Widget-Stile */
QWidget {{
    background-color: {SURFACE};
    color: {TEXT};
    font-family: 'Noto Sans', 'Inter', 'Cantarell', 'Ubuntu', 'DejaVu Sans', sans-serif;
    font-size: 12px;
}}

QMainWindow, QDialog {{
    background-color: {WINDOW};
}}

/* Menüleiste */
QMenuBar {{
    background-color: {WINDOW};
    color: {TEXT_MUTED};
    padding: 2px;
    border-bottom: 1px solid {BORDER_SOFT};
}}
QMenuBar::item {{
    background: transparent;
    padding: 4px 10px;
    border-radius: 4px;
}}
QMenuBar::item:selected {{
    background-color: {SURFACE_RAISED};
    color: {TEXT};
}}
QMenu {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    padding: 4px;
}}
QMenu::item {{
    padding: 5px 22px 5px 18px;
    border-radius: 4px;
}}
QMenu::item:selected {{
    background-color: {ACCENT};
    color: #ffffff;
}}
QMenu::separator {{
    height: 1px;
    background: {BORDER_SOFT};
    margin: 4px 6px;
}}

/* Toolbar */
QToolBar {{
    background-color: {SURFACE};
    border: none;
    border-bottom: 1px solid {BORDER_SOFT};
    padding: 4px 8px;
    spacing: 6px;
}}
QToolBar QToolButton {{
    background: transparent;
    padding: 5px 8px;
    border-radius: 5px;
    color: {TEXT_MUTED};
    font-weight: 500;
}}
QToolBar QToolButton:hover {{
    background-color: {SURFACE_RAISED};
    color: {TEXT};
}}
QToolBar QToolButton:checked {{
    background-color: rgba(61, 174, 233, 0.25);
    color: {ACCENT};
    border: 1px solid {ACCENT};
}}
QToolBar::separator {{
    width: 1px;
    background: {BORDER};
    margin: 4px 6px;
}}

/* Statusleiste */
QStatusBar {{
    background-color: {WINDOW};
    color: {TEXT_MUTED};
    border-top: 1px solid {BORDER_SOFT};
}}
QStatusBar::item {{ border: none; }}

/* ScrollBars */
QScrollBar:vertical {{
    border: none;
    background-color: {SURFACE_SUNKEN};
    width: 8px;
    margin: 0px;
}}
QScrollBar::handle:vertical {{
    background-color: {BORDER};
    min-height: 24px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical:hover {{ background-color: #4b535a; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
QScrollBar:horizontal {{
    border: none;
    background-color: {SURFACE_SUNKEN};
    height: 8px;
    margin: 0px;
}}
QScrollBar::handle:horizontal {{
    background-color: {BORDER};
    min-width: 24px;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal:hover {{ background-color: #4b535a; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0px; }}

/* GroupBox */
QGroupBox {{
    background-color: {SURFACE};
    border: 1px solid {BORDER_SOFT};
    border-radius: 6px;
    margin-top: 18px;
    padding: 12px 10px 10px 10px;
    font-weight: bold;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 4px;
    color: {ACCENT};
}}

/* Buttons */
QPushButton {{
    background-color: {SURFACE_RAISED};
    border: 1px solid {BORDER};
    padding: 5px 12px;
    border-radius: 4px;
    color: {TEXT};
    font-weight: 500;
}}
QPushButton:hover {{
    background-color: rgba(239, 240, 241, 0.08);
    border-color: {ACCENT};
    color: {TEXT};
}}
QPushButton:pressed {{
    background-color: {ACCENT_DARK};
    border-color: {ACCENT_DARK};
    color: #ffffff;
}}
QPushButton:disabled {{
    background-color: {SURFACE_SUNKEN};
    border-color: {BORDER_SOFT};
    color: {TEXT_DISABLED};
}}

/* Start / Berechnen Button (grün im LME-Stil) */
QPushButton#btn_start {{
    background-color: {START_GREEN};
    color: #ffffff;
    border: 1px solid {START_GREEN};
    font-weight: bold;
    padding: 6px 16px;
}}
QPushButton#btn_start:hover {{
    background-color: {START_GREEN_HOVER};
    border-color: {START_GREEN_HOVER};
}}
QPushButton#btn_start:pressed {{ background-color: #218c4e; }}

/* Stop / Play Button */
QPushButton#btn_play {{
    background-color: {ACCENT_DARK};
    color: #ffffff;
    border: 1px solid {ACCENT};
    font-weight: bold;
    padding: 5px 12px;
}}
QPushButton#btn_play:hover {{
    background-color: {ACCENT};
}}
QPushButton#btn_play.playing {{
    background-color: {STOP_RED};
    border-color: {STOP_RED};
}}

/* Eingabefelder */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QTimeEdit {{
    background-color: {SURFACE_SUNKEN};
    border: 1px solid {BORDER};
    padding: 4px 6px;
    border-radius: 4px;
    color: {TEXT};
    selection-background-color: {ACCENT};
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus, QTimeEdit:focus {{
    border-color: {ACCENT};
    background-color: rgba(61, 174, 233, 0.08);
}}
QComboBox::drop-down, QDateEdit::drop-down, QTimeEdit::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 20px;
    border-left: 1px solid {BORDER_SOFT};
}}
QComboBox QAbstractItemView {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 4px;
    selection-background-color: {ACCENT};
    selection-color: #ffffff;
    padding: 2px;
    outline: none;
}}

/* Tabellen */
QTableWidget, QTreeWidget, QListWidget {{
    background-color: {SURFACE_SUNKEN};
    border: 1px solid {BORDER_SOFT};
    border-radius: 6px;
    gridline-color: {BORDER_SOFT};
    selection-background-color: rgba(61, 174, 233, 0.28);
    selection-color: #ffffff;
    alternate-background-color: #26292d;
    outline: none;
}}
QTableWidget::item {{
    padding: 4px 6px;
    border-bottom: 1px solid #262a2e;
}}
QTableWidget::item:selected {{
    background-color: rgba(61, 174, 233, 0.35);
    color: #ffffff;
}}
QHeaderView::section {{
    background-color: {SURFACE_RAISED};
    color: {TEXT_MUTED};
    padding: 6px;
    border: none;
    border-bottom: 1px solid {BORDER_SOFT};
    border-right: 1px solid {BORDER_SOFT};
    font-weight: bold;
    font-size: 11px;
}}
QTableCornerButton::section {{ background-color: {SURFACE_RAISED}; border: none; }}

/* Tabs */
QTabWidget::pane {{
    border: 1px solid {BORDER_SOFT};
    border-radius: 6px;
    background-color: {SURFACE};
    top: -1px;
}}
QTabBar::tab {{
    background-color: {SURFACE_SUNKEN};
    color: {TEXT_MUTED};
    padding: 6px 14px;
    border: 1px solid {BORDER_SOFT};
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    margin-right: 2px;
    font-weight: 500;
}}
QTabBar::tab:selected {{
    background-color: {SURFACE};
    color: {TEXT};
    border-color: {BORDER_SOFT};
    border-top: 2px solid {ACCENT};
}}
QTabBar::tab:hover:!selected {{ color: {TEXT}; background-color: {SURFACE_RAISED}; }}

/* ProgressBars */
QProgressBar {{
    border: 1px solid {BORDER_SOFT};
    background-color: {SURFACE_SUNKEN};
    text-align: center;
    color: {TEXT};
    font-weight: bold;
    height: 14px;
    border-radius: 3px;
    font-size: 10px;
}}
QProgressBar::chunk {{
    background-color: {ACCENT};
    border-radius: 2px;
}}

/* Sliders */
QSlider::groove:horizontal {{
    height: 4px;
    background: {BORDER};
    border-radius: 2px;
}}
QSlider::sub-page:horizontal {{
    background: {ACCENT};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {TEXT};
    border: 1px solid {BORDER_SOFT};
    width: 14px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 7px;
}}
QSlider::handle:horizontal:hover {{
    background: {ACCENT_HOVER};
}}

/* Splitter */
QSplitter::handle {{
    background-color: {BORDER_SOFT};
}}
QSplitter::handle:horizontal {{
    width: 3px;
}}
QSplitter::handle:vertical {{
    height: 3px;
}}
QSplitter::handle:hover {{
    background-color: {ACCENT};
}}

/* TextEdit / Deutung */
QTextEdit {{
    background-color: {SURFACE_SUNKEN};
    border: 1px solid {BORDER_SOFT};
    border-radius: 4px;
    padding: 6px;
    color: {TEXT};
    line-height: 1.4;
}}
"""
